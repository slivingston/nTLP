#!/usr/bin/env python
"""
Test TuLiP code for working with (proposition preserving) partitions.

SCL; 18 October 2012.
"""

from tulip.prop2part import prop2part2
import tulip.polytope as pc
import numpy as np


class basic_partition_test:

    def setUp(self):
        # (based on test code previously at the bottom of tulip/prop2part.py.)
        domain_poly_A = np.array(np.vstack([np.eye(2),-np.eye(2)]))
        domain_poly_b = np.array([2., 2, 0, 0]).T
        self.state_space = pc.Polytope(domain_poly_A, domain_poly_b)

        cont_props = []
        A = []
        b = []
        A.append(np.array([[1., 0.],
                           [-1., 0.],
                           [0., 1.],
                           [0., -1.]]))
        b.append(np.array([[1., 0., 1., 0.]]).T)
        cont_props.append(pc.Polytope(A[0], b[0]))

        A.append(np.array([[1., 0.],
                           [-1., 0.],
                           [0., 1.],
                           [0., -1.]]))
        b.append(np.array([[1., 0., 2., -1.]]).T)
        cont_props.append(pc.Polytope(A[1], b[1]))

        A.append(np.array([[1., 0.],
                           [-1., 0.],
                           [0., 1.],
                           [0., -1.]]))
        b.append(np.array([[2., -1., 1., 0.]]).T)
        cont_props.append(pc.Polytope(A[2], b[2]))

        A.append(np.array([[1., 0.],
                           [-1., 0.],
                           [0., 1.],
                           [0., -1.]]))
        b.append(np.array([[2., -1., 2., -1.]]).T)
        cont_props.append(pc.Polytope(A[3], b[3]))

        self.cont_props_dict = dict([("C"+str(i), pc.Polytope(A[i], b[i])) for i in range(4)])

    def tearDown(self):
        self.state_space = None
        self.cont_props_dict = None

    def test_prop2part2(self):
        # (based on test code previously at the bottom of tulip/prop2part.py.)
        mypartition = prop2part2(self.state_space, self.cont_props_dict)

        # A4 = np.array([[1., 0.],
        #                [-1., 0.],
        #                [0., 1.],
        #                [0., -1.]])
        # b4 = np.array([[0.5, 0., 0.5, 0.]]).T
        # poly1 = pc.Polytope(A4,b4)
        # r1 = pc.mldivide(mypartition.list_region[3],poly1)

        ref_adjacency = np.array([[1,1,1,0],[1,1,0,1],[1,0,1,1],[0,1,1,1]])
        assert np.all(mypartition.adj == ref_adjacency)

        assert len(mypartition.list_region) == 4
        for reg in mypartition.list_region:
            assert len(reg.list_prop) == 4
            assert len(reg.list_poly) == 1
            i = [i for i in range(len(reg.list_prop)) if reg.list_prop[i] == 1]
            assert len(i) == 1
            i = i[0]
            assert self.cont_props_dict.has_key(mypartition.list_prop_symbol[i])
            ref_V = pc.extreme(self.cont_props_dict[mypartition.list_prop_symbol[i]])
            ref_V = set([(v[0],v[1]) for v in ref_V.tolist()])
            actual_V = pc.extreme(reg.list_poly[0])
            actual_V = set([(v[0],v[1]) for v in actual_V.tolist()])
            assert ref_V == actual_V

    def test_copy(self):
        # Test copy method of PropPreservingPartition class
        P = prop2part2(self.state_space, self.cont_props_dict)
        Q = P.copy()
        assert P is not Q
        assert P.adj is not Q.adj
        assert np.all(P.adj == Q.adj)
        assert len(P.list_region) == len(Q.list_region)
        for j in range(len(P.list_region)):
            r = P.list_region[j]
            s = Q.list_region[j]
            assert r is not s
            assert len(r.list_poly) == len(s.list_poly)
            assert np.all([r.list_poly[i].A.shape == s.list_poly[i].A.shape for i in range(len(r.list_poly))]) and np.all([r.list_poly[i].b.shape == s.list_poly[i].b.shape for i in range(len(r.list_poly))])
            assert np.all([np.all(r.list_poly[i].A == s.list_poly[i].A) for i in range(len(r.list_poly))]) and np.all([np.all(r.list_poly[i].b == s.list_poly[i].b) for i in range(len(r.list_poly))])
            assert np.all([r.list_poly[i] is not s.list_poly[i] for i in range(len(r.list_poly))])
