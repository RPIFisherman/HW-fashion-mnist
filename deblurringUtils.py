# resource for the Haar matrices: https://www.cis.upenn.edu/~cis515/cis515-20-sl-Haar.pdf
import numpy as np
from numpy.linalg import matrix_power
import matplotlib.pyplot as plt

from skimage.util import img_as_float
from skimage.transform import resize
from skimage.exposure import rescale_intensity, equalize_hist
from scipy.linalg import toeplitz, khatri_rao
from scipy.sparse.linalg import LinearOperator

# implements recursive definition of Haar Matrix given on page 154 of the reference

def haarMatrix(n, normalized=False):
    # Allow only size n of power 2
    n = int(2**np.ceil(np.log2(n)))

    if n == 2:
        H = np.array([[1,1], [1, -1]])
    else:
        Hprev = haarMatrix(n//2)
        Left = np.kron(Hprev, [[1], [1]])
        Right = np.kron(np.eye(n//2), [[1], [-1]])
        H = np.hstack((Left, Right))
    
    if normalized:
        d = np.zeros(n)
        d[0] = 1/np.sqrt(n)
        start = 1
        for r in np.arange(int(np.log2(n))):
            d[start:start+2**r] = np.power(2, -(np.log2(n)-r)/2)
            start = start + 2**r
        H = H @ np.diag(d)
    return H

def vectorized2DHaarMatrix(m, n, d=1):
    # Let H_n be an orthonormal haar matrix of size 2^n. Then the 2d Haar transform of a 2^m by 2^n matrix A is given by
    # H_m A H_n^T
    # This corresponds to mapping vec(A) to M vec(A), where M = (H_n \otimes H_m)
    # This function returns M^d, corresponding to taking the 2D Haar transformation d times
    
    Hcols = matrix_power(haarMatrix(m, normalized=True), d)
    Hrows = matrix_power(haarMatrix(n, normalized=True), d)
    
    return np.kron(Hrows, Hcols) 

def blurMatrix(m,width=3):
    # width should be odd
    halflen = int(np.ceil((width-1)/2))
    
    r, c = np.zeros(m), np.zeros(m)
    c[:1+halflen] = 1/width
    r[:1+halflen] = 1/width
    
    return toeplitz(c, r)

def fastKronVecProd(A, B, v):
    # compute (A \otimes B) v
    m, n = B.shape
    vcols = np.reshape(v, (n, A.shape[1]), order='F' )
    return khatri_rao(A, B @ vcols).sum(axis=1)
    
    
def vectorized2DBlurMatrix(m, n, width=3):
    # This function returns B corresponding to blurring the columns and rows of an image independently using averaging filters with the same filter width, and
    # represents this process as a matrix operating on the mn vector obtained by vectorizing the image
    Bcols = blurMatrix(m, width)
    Brows = blurMatrix(n, width)
    
    return np.kron(Brows, Bcols)
    
def vectorize(im):
    # stacks columns into a vector
    m, n = im.shape
    return np.reshape(im, m*n, order='F')

def unvectorize(vec, m, n):
    # adjoint of vectorize
    return np.reshape(vec, [m,n], order='F')

def rescale(im):
    # scales entries in im to min 0 and max 1
    return rescale_intensity(im, out_range=(0,1))
    
def visualize(im):
    # takes a floating point array and visualizes as an image
    plt.figure(figsize=(4,4))
    plt.imshow(rescale(im), cmap='gray', clim=(0,1), interpolation='nearest')
    plt.tight_layout()
    plt.show()
    
def genBH(n, blursize):
    # returns (B, H) a blurring matrix for an n-by-n image, as a LinearOperator, and H, the
    # Haar transform
    
    Hn = haarMatrix(n, normalized=True)
    HnT = Hn.T.copy()
    def applyH(v):
        return fastKronVecProd(Hn, Hn, v)
    def applyHT(v):
        return fastKronVecProd(HnT, HnT, v)
    H = LinearOperator((n**2, n**2), matvec = applyH, rmatvec = applyHT)
    
    Brows = blurMatrix(n, width=blursize)
    BrowsT = Brows.T.copy()
    Bcols = blurMatrix(n, width=blursize)
    BcolsT = Bcols.T.copy()
    def applyB(v):
        return fastKronVecProd(Brows, Bcols, v)
    def applyBT(v):
        return fastKronVecProd(BrowsT, BcolsT, v)
    B = LinearOperator((n**2, n**2), matvec = applyB, rmatvec = applyBT)
    
    return B, H
    
def getrow(B, i):
    # returns the ith row of a LinearOperator, as a column vector
    ei = np.zeros(B.shape[0])
    ei[i-1] = 1.0
    return (B.T @ ei)[np.newaxis]