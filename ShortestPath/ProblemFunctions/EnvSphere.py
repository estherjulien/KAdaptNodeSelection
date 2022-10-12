import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import pickle
import math

"""
Code for making a 3-D graph on a sphere as a shortest path instance
"""


class Graph:
    def __init__(self, N, gamma=7, inst_num=0, degree=5, throw_away_perc=0.9, init_vertices=None, init_distances=None, init_s=None, init_t=None, plot=False):
        self.N = N
        self.degree = degree
        self.throw_away_perc = throw_away_perc
        if init_vertices is None:
            self.vertices, init_arcs = self.init_graph()
        else:
            self.vertices = init_vertices
        if init_distances is None:
            self.distances, self.s, self.t = self.update_graph(init_arcs, throw_away_perc)
        else:
            self.distances = init_distances
            self.s = init_s
            self.t = init_t
        self.arcs = self.distances > 1e-5
        self.num_arcs = int(self.arcs.sum())
        self.xi_dim = self.num_arcs
        self.x_dim = self.num_arcs
        self.y_dim = self.num_arcs

        self.arcs_array = np.array([[i, j] for i in np.arange(self.N) for j in np.arange(self.N) if self.arcs[i, j]])
        self.distances_array = np.array([self.distances[i, j] for i, j in self.arcs_array])
        self.arcs_in, self.arcs_out = self.in_out_arcs()

        self.bigM = sum(self.distances_array)*3
        self.upper_bound = sum(self.distances_array)*3
        self.inst_num = inst_num
        self.init_uncertainty = np.zeros(self.num_arcs)

        if gamma is not None:
            self.gamma = gamma
        if plot:
            self.plot_graph()

    def set_gamma(self, gamma):
        self.gamma = gamma

    def vertices_fun(self):
        vec = np.random.randn(3, self.N)
        vec /= np.linalg.norm(vec, axis=0)
        return vec.transpose()

    def init_graph(self):
        vertices = self.vertices_fun()
        # make initial arcs
        arcs = np.ones([self.N, self.N], dtype=np.float)
        for i in np.arange(self.N):
            for j in np.arange(self.N):
                if i == j:
                    arcs[i, j] = 0
        return vertices, arcs

    def update_graph(self, arcs, throw_away_perc):
        # delete arcs with middle in no go zones
        arc_dict = dict()
        for i in np.arange(self.N):
            for j in np.arange(self.N):
                if arcs[i, j] < 1e-5:
                    continue
                distance = self.spherical_distance(i, j)
                arcs[i, j] = distance
                arc_dict[(i, j)] = distance
        # delete long arcs (first sort and then sth percent)
        arc_dict_order = {k: v for k, v in sorted(arc_dict.items(), key=lambda item: -item[1])}
        arc_list_order = list(arc_dict_order)
        # first ones are s and t!
        s, t = arc_list_order[0]
        # delete "throw_away_perc" longest arcs
        throw_away_num = np.floor(len(arc_dict_order)*throw_away_perc)
        in_degrees = {i: sum([arcs[:, i] > 1e-5][0]) for i in np.arange(self.N)}
        out_degrees = {i: sum([arcs[i, :] > 1e-5][0]) for i in np.arange(self.N)}
        del_arc = 0
        while del_arc < throw_away_num:
            # check here if when you delete this, degree out and in will be >= 1 and total degree >= min_degree
            try:
                i, j = arc_list_order[del_arc]
            except KeyError:
                break
            # check in degree of j
            if in_degrees[j] <= self.degree:
                del_arc += 1
                continue
            # check out degree of i
            if out_degrees[i] <= self.degree:
                del_arc += 1
                continue
            # check each time if you can delete this arc based on connected graph
            arcs[i, j] = 0
            in_degrees[j] -= 1
            out_degrees[i] -= 1
            del_arc += 1
        return arcs, s, t

    def spherical_distance(self, i, j):
        dist = math.sqrt(sum((self.vertices[i][d] - self.vertices[j][d])**2 for d in np.arange(3)))
        phi = math.asin(dist/2)
        return 2*phi

    def in_out_arcs(self):
        arcs_in = {i: [] for i in np.arange(self.N)}
        arcs_out = {i: [] for i in np.arange(self.N)}
        for a in np.arange(self.num_arcs):
            i, j = self.arcs_array[a]
            arcs_in[j].append(a)
            arcs_out[i].append(a)
        return arcs_in, arcs_out

    # plot graphs
    def plot_graph(self, problem_type="", name=None):
        sns.set()
        sns.set_style("whitegrid")

        phi = np.linspace(0, np.pi, 20)
        theta = np.linspace(0, 2 * np.pi, 40)
        x = np.outer(np.sin(theta), np.cos(phi))
        y = np.outer(np.sin(theta), np.sin(phi))
        z = np.outer(np.cos(theta), np.ones_like(phi))

        fig, ax = plt.subplots(1, 1, subplot_kw={'projection': '3d'})
        ax.plot_wireframe(x, y, z, color='lightgray', rstride=1, cstride=1)

        for i in np.arange(self.N):
            for j in np.arange(self.N):
                if self.arcs[i, j] < 1e-5:
                    continue
                plt.plot(self.vertices[[i, j], 0], self.vertices[[i, j], 1], self.vertices[[i, j], 2], "k")
        graph_vertices = [i for i in np.arange(self.N) if i not in [self.s, self.t]]
        ax.scatter(self.vertices[graph_vertices, 0], self.vertices[graph_vertices, 1], self.vertices[graph_vertices, 2], s=100, c='r')
        ax.scatter(*self.vertices[self.s], s=200, c="g")
        ax.scatter(*self.vertices[self.t], s=200, c="b")

        plt.axis("off")

        if name is None:
            plt.savefig(f"ShortestPathCluster/Data/Plots/graph_{problem_type}_inst{self.inst_num}")
        else:
            pickle.dump(fig, open(f'Data/Plots/Interactive/FigureObject_graph_{name}_{problem_type}_{self.inst_num}.fig.pickle', 'wb'))
            plt.savefig(f"Data/Plots/graph_{name}_{problem_type}_inst{self.inst_num}")

        return plt

    def plot_graph_solutions(self, K, y, tau, x=None, tmp=False, it=0, alg_type="rand"):
        plt = self.plot_graph()

        # second stage
        cols = ["blue", "purple", "green", "red", "yellow", "orange", "grey", "cornflowerblue", "hotpink"]
        for k in np.arange(K):
            if len(tau[k]) == 0:
                continue
            for a in np.arange(self.num_arcs):
                if y[k][a] > 0.5:
                    i, j = self.arcs_array[a]
                    plt.plot(self.vertices[[i, j], 0], self.vertices[[i, j], 1], self.vertices[[i, j], 3], cols[k])

        if tmp:
            plt.savefig(f"Results/Plots/tmp_graph_{alg_type}_inst{self.inst_num}_it{it}")
        else:
            plt.savefig(f"Results/Plots/final_graph_{alg_type}_inst{self.inst_num}")
            plt.savefig(f"Results/Plots/final_graph_{alg_type}_inst{self.inst_num}.pdf")
        plt.close()
