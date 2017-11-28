from __future__ import absolute_import, print_function, division

import numpy
import pytest

import loopy as lp

from ufl import (Mesh, FunctionSpace, FiniteElement, VectorElement,
                 Coefficient, TestFunction, TrialFunction, dx, div,
                 inner, interval, triangle, tetrahedron, dot, grad)

from tsfc import compile_form


def mass(cell, degree):
    m = Mesh(VectorElement('CG', cell, 1))
    V = FunctionSpace(m, FiniteElement('CG', cell, degree))
    u = TrialFunction(V)
    v = TestFunction(V)
    return u*v*dx


def poisson(cell, degree):
    m = Mesh(VectorElement('CG', cell, 1))
    V = FunctionSpace(m, FiniteElement('CG', cell, degree))
    u = TrialFunction(V)
    v = TestFunction(V)
    return dot(grad(u), grad(v))*dx


def helmholtz(cell, degree):
    m = Mesh(VectorElement('CG', cell, 1))
    V = FunctionSpace(m, FiniteElement('CG', cell, degree))
    u = TrialFunction(V)
    v = TestFunction(V)
    return (u*v + dot(grad(u), grad(v)))*dx


def elasticity(cell, degree):
    m = Mesh(VectorElement('CG', cell, 1))
    V = FunctionSpace(m, VectorElement('CG', cell, degree))
    u = TrialFunction(V)
    v = TestFunction(V)

    def eps(u):
        return 0.5*(grad(u) + grad(u).T)
    return inner(eps(u), eps(v))*dx


def count_flops(form):
    kernel, = compile_form(form, parameters=dict(mode='tensor'))

    op_map = lp.get_op_map(kernel.ast)
    op_map = op_map.filter_by(dtype=[numpy.float], name=["add", "sub", "mul", "div"])

    return op_map.sum().eval_with_dict({})


@pytest.mark.skip(reason="skip due to loopy limitation")
@pytest.mark.parametrize('form', [mass, poisson, helmholtz, elasticity])
@pytest.mark.parametrize(('cell', 'order'),
                         [(interval, 2),
                          (triangle, 4),
                          (tetrahedron, 6)])
def test_bilinear(form, cell, order):
    degrees = numpy.arange(1, 9 - 2 * cell.topological_dimension())
    flops = [count_flops(form(cell, int(degree)))
             for degree in degrees]
    rates = numpy.diff(numpy.log(flops)) / numpy.diff(numpy.log(degrees + 1))
    assert (rates < order).all()


@pytest.mark.skip(reason="skip due to loopy limitation")
@pytest.mark.parametrize(('cell', 'order'),
                         [(interval, 1),
                          (triangle, 2),
                          (tetrahedron, 3)])
def test_linear(cell, order):
    def form(cell, degree):
        m = Mesh(VectorElement('CG', cell, 1))
        V = FunctionSpace(m, FiniteElement('CG', cell, degree))
        v = TestFunction(V)
        return v*dx

    degrees = numpy.arange(2, 9 - 1.5 * cell.topological_dimension())
    flops = [count_flops(form(cell, int(degree)))
             for degree in degrees]
    rates = numpy.diff(numpy.log(flops)) / numpy.diff(numpy.log(degrees + 1))
    assert (rates < order).all()


@pytest.mark.skip(reason="skip due to loopy limitation")
@pytest.mark.parametrize(('cell', 'order'),
                         [(interval, 1),
                          (triangle, 2),
                          (tetrahedron, 3)])
def test_functional(cell, order):
    def form(cell, degree):
        m = Mesh(VectorElement('CG', cell, 1))
        V = FunctionSpace(m, VectorElement('CG', cell, degree))
        f = Coefficient(V)
        return div(f)*dx

    dim = cell.topological_dimension()
    degrees = numpy.arange(1, 7 - dim) + (3 - dim)
    flops = [count_flops(form(cell, int(degree)))
             for degree in degrees]
    rates = numpy.diff(numpy.log(flops)) / numpy.diff(numpy.log(degrees + 1))
    assert (rates < order).all()


def test_mini():
    m = Mesh(VectorElement('CG', triangle, 1))
    P1 = FiniteElement('Lagrange', triangle, 1)
    B = FiniteElement("Bubble", triangle, 3)
    V = FunctionSpace(m, VectorElement(P1 + B))
    u = TrialFunction(V)
    v = TestFunction(V)
    a = inner(grad(u), grad(v))*dx
    count_flops(a)


if __name__ == "__main__":
    import os
    import sys
    pytest.main(args=[os.path.abspath(__file__)] + sys.argv[1:])
