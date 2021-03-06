import numpy as np
from scipy.fft import fft, ifft

##################################################
## Library of general purpose math functions
##################################################
## Author: Clayton Seitz
## Copyright: 2021, The Hebb Project
## Email: cwseitz@uchicago.edu
##################################################

def mean_field_rates(N, mxe, mxi, w_ee, w_ii, w_ei, w_ie, thr, tau_e, tau_i):

    """
    Computes the mean rates of excitatory and inhbitory neurons
    in the mean-field approximation

    Parameters
    ----------
    """

    r_e = (mxe*w_ii - mxi*w_ie)/(w_ei*w_ie - w_ee*w_ii)
    r_i = (mxe*w_ei - mxi*w_ee)/(w_ei*w_ie - w_ee*w_ii)

    # a = mxe*w_ii - mxi*w_ie
    # b = mxe*w_ei - mxi*w_ee
    # c = w_ei*w_ie - w_ee*w_ii

    # r_e = (a - mxe*thr*tau_i/np.sqrt(N))
    # r_e /= c + thr*(w_ee*tau_e + w_ii*tau_e)/np.sqrt(N) - (tau_e*tau_i*thr**2)/N
    #
    # r_i = (b - mxi*thr*tau_e/np.sqrt(N))
    # r_i /= c + thr*(w_ee*tau_i + w_ii*tau_i)/np.sqrt(N) - (tau_e*tau_i*thr**2)/N

    return r_e, r_i

def block_fft(x, n, magnitude=False):

    """
    Computes the discrete fast fourier transform for a tensor
    of synaptic currents with shape (N,trials,time). The transform
    is computed along the time axis. Returns the complex valued
    tensor, and the user is responsible for computing its magnitude
    for conversion to power spectra

    Parameters
    ----------
    """

    x_t = fft(x,n,axis=-1)
    if magnitude:
        x_t = np.abs(x_t)
    return x_t

def block_spectra(x,n,magnitude=False):

    """
    Computes the cross-spectral densities and auto-spectral densities
    given a tensor of synaptic currents with shape N,trials,time)
    It is computed as the product of of all possible pairs in the frequency domain
    with complex conjugation of the first signal

    Parameters
    ----------
    """

    x_t = block_fft(x,n,magnitude=False)
    trials = x_t.shape[1]
    nsteps = x_t.shape[-1]

    arr = []
    #iterate over trials
    for i in range(trials):
        a = x_t[:,i,:].conj()
        b = x_t[:,i,:]
        c = np.einsum('ij,kj->ikj',a,b)
        arr.append(c)
    arr = np.array(arr)
    arr = np.moveaxis(arr,0,2)

    if magnitude:
        arr = np.abs(arr)
    arr /= nsteps #1/T factor

    return arr

def block_cc(x,n):

    """
    Computes the cross-correlation of a tensor of synaptic currents with shape
    (N,trials,time) with itself along the time axis. It is computed by first
    computing the cross spectrum and then transforming back into the time domain

    Parameters
    ----------
    """

    x_t = block_spectra(x,n,magnitude=False)
    cc = np.real(ifft(x_t,axis=-1))
    return cc

def multi_gauss(X, mu, cov):

    """
    A multivariate gaussian defined over a discrete space X
    This is NOT a probability density function (PDF) unless you make it one
    with the appropriate normalization

    Parameters
    ----------
    X : ndarray
        The domain over which to evaluate the multivariate gaussian
    mu : ndarray
        A vector defining the central coordinate for the gaussian
    cov : ndarray
        Covariance tensor

    """

    n = mu.shape[0]
    det = np.linalg.det(cov)
    inv = np.linalg.inv(cov)
    fac = np.einsum('...k,kl,...l->...', X-mu, inv, X-mu)
    return np.exp(-fac / 2)

def multi_gauss_prod(mu_1, cov_1, mu_2, cov_2):

    """
    Returns the mu vector and covariance tensor for a multivariate
    gaussian constructed as the product of two multivariate gaussians

    Parameters
    ----------
    mu_1 : ndarray
        Central coordinate of the first multi gaussian
    cov_1 : ndarray
        Covariance tensor of the first multi gaussian
    mu_2 : ndarray
        Central coordinate of the second multi gaussian
    cov_2 : ndarray
        Covariance tensor of the second multi gaussian

    """

    mu_3 = cov_2 @ np.linalg.inv(cov_1+cov_2) @ mu_1 +\
           cov_1 @ np.linalg.inv(cov_1+cov_2) @ mu_2

    cov_3 = cov_1 @ np.linalg.inv(cov_1+cov_2) @ cov_2

    return mu_3, cov_3

def delta_gauss(dx, sigma, delta):

    """
    Return the value of a gaussian a distance dx from the mean
    Useful when only a single sample is needed rather than the entire function

    Parameters
    ----------
    dx : float
        Distance from the center
    sigma : float
        Standard deviation of the gaussian
    delta : float
        Grid spacing

    Returns
    --------
    val : float
        Value of the gaussian a distance dx from the center

    """

    dx *= delta
    val = np.exp((-0.5*dx**2)/sigma**2)
    return val

def torgauss(X, Y, x0, y0, sigma, delta=1):

    """
    Return a symmetric gaussian function centered at (x0,y0) sampled on a
    two-dimensional grid with periodic boundary conditions (a torus)

    Parameters
    ----------
    N : int
        Total number of grid points
    x0 : float
        X-coordinate of the center of the gaussian
    y0 : float
        Y-coordinate of the center of the gaussian
    sigma : ndarray
        Standard deviation of the gaussian

    Returns
    --------
    Z : ndarray
        A two-dimensional gaussian with shape (sqrt(N),sqrt(N))

    """

    d = tordistv(X, Y, x0, y0)
    Z = np.exp(-(0.5*d**2)/sigma**2)
    M = M = int(round(np.sqrt(X.shape[0])))
    Z = Z.reshape((M,M))

    return Z

def tordistv(X, Y, x0, y0, delta=1):

    """
    A vectorized version of the tordist function

    Evaluates the Euclidean distance between two points on a discrete
    torus (a 2D lattice with periodic boundary conditions)

    Parameters
    ----------
    M : int
        The number of grid points along an axis
    x0 : float
        X-coordinate of the center of the gaussian
    y0 : float
        Y-coordinate of the center of the gaussian
    X : ndarray
        X-coordinates of points to calculate distance
    Y : ndarray
        Y-coordinates of points to calculate distance

    Returns
    --------
    dr : ndarray, (M**2,)
        Euclidean distances between points (X,Y) and (x0,y0)

    """

    M = int(round(np.sqrt(X.shape[0])))
    dx = np.minimum(np.abs(X-x0),M*delta-np.abs(X-x0))
    dy = np.minimum(np.abs(Y-y0),M*delta-np.abs(Y-y0))
    dr = np.sqrt(dx**2 + dy**2)
    return dr

def tordist(r_i, r_j, M, delta):

    """
    A vectorized version of the tordist function

    Evaluates the Euclidean distance between two points on a discrete
    torus (a 2D lattice with periodic boundary conditions)

    Parameters
    ----------
    r_i : tuple,
        Coordinate pair for position i
    r_j : tuple,
        Coordinate pair for position j
    M : int,
        The number of grid points along an axis
    delta : float,
        Grid spacing

    Returns
    --------
    dr : float,
        Euclidean distances between points r_i and r_j

    """

    x1, y1 = r_i; x2, y2 = r_j
    dx = np.minimum(np.abs(x1-x2),M*delta-np.abs(x1-x2))
    dy = np.minimum(np.abs(y1-y2),M*delta-np.abs(y1-y2))
    dr = np.sqrt(dx**2 + dy**2)
    return dr


def sample_trinomial(a,b,c, return_sample=False):

    """
    Draw a sample from a trinomial distribution (a categorical distribution
    with three possibilities a,b,c. Inputs a,b,c should be binomial
    probabilities in [0,1]

    Parameters
    ----------
    a : ndarray,
        Binomial probability of category a being observed
    b : ndarray,
        Binomial probability of category b being observed
    c : ndarray,
        Binomial probability of category c being observed

    Returns
    --------
    out : ndarray,
        A sample from the trinomial distribution encoded as
        (a,b,c) = (-1,1,0)

    """

    a = np.atleast_1d(a)
    b = np.atleast_1d(b)
    c = np.atleast_1d(c)
    p_a, p_b, p_c = trinomial(a,b,c)
    x = np.random.uniform(0,1,size=a.shape)
    out = np.zeros_like(x)
    out[np.where(np.logical_and(x > 0, x <= p_a))] = 1
    out[np.where(np.logical_and(x > p_a, x <= p_a+p_b))] = -1
    out[np.where(x > p_a+p_b)] = 0
    if out.shape == (1,): out = out.item()

    return out

def trinomial(a,b,c):

    """
    Construct the trinomial distribution from three binomial probabilities
    provided by the user. This function will handle the case where
    a = 1 and b = 1 by setting all probabilities to zero, This would represent
    a neuron being connected to itself (an autapse), which we do not allow

    Parameters
    ----------
    a : float,
        Binomial probability of category a being observed
    b : float,
        Binomial probability of category b being observed
    c : float,
        Binomial probability of category c being observed

    Returns
    --------
    out : int,
        Probabilities of each of the categories

    """

    p_a = a*(1-b)*(1-c)
    p_b = b*(1-a)*(1-c)
    p_c = c*(1-a)*(1-b)
    z = p_a + p_b + p_c
    p_a = np.divide(p_a, z, out=np.zeros_like(p_a), where=z!=0)
    p_b = np.divide(p_b, z, out=np.zeros_like(p_b), where=z!=0)
    p_c = np.divide(p_c, z, out=np.zeros_like(p_c), where=z!=0)

    return p_a, p_b, p_c


def entropy(p):

    """
    Compute the entropy of a probability distribution p

    Parameters
    ----------
    p : ndarray,
        Probability distribution

    Returns
    --------
    H : float,
        Entropy of p expressed in units of bits
    """

    H = np.sum(p*np.log2(1/p))
    return H
