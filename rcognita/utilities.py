from svgpath2mpl import parse_path
import numpy as np
from numpy.matlib import repmat
import matplotlib as mpl
import inspect

# hidden tests
def check_call(func):
    def wrapper(*args):
        func(*args)
        setattr(*args, 'func_has_been_called', True)
    return wrapper

# classes

class Generic:
    @classmethod
    @check_call
    def print_docstring(cls):
        print(cls.__doc__)

    @classmethod
    @check_call
    def print_init_params(cls):
        signature = inspect.signature(cls.__init__)
        for i, param in enumerate(signature.parameters.values()):
            if i == 0:
                pass
            else:
                print(param)

class _model:
    """ Class of estimated models             
        
    Parameters
    ---------- 
    A, B, C, D : : arrays of proper shape
        State-space _model parameters
    x0set : : array
        Initial state estimate
        
    **When introducing your custom _model estimator, adjust this class**    
        
    """
    
    def __init__(self, A, B, C, D, x0est):
        self.A = A
        self.B = B
        self.C = C
        self.D = D
        self.x0est = x0est
        
    def updatePars(self, Anew, Bnew, Cnew, Dnew):
        self.A = Anew
        self.B = Bnew
        self.C = Cnew
        self.D = Dnew
        
    def updateIC(self, x0setNew):
        self.x0set = x0setNew

class _ZOH:
    """
    Zero-order hold
    
    """    
    def __init__(self, initTime=0, initVal=0, samplTime=1):
        self.timeStep = initTime
        self.samplTime = samplTime
        self.currVal = initVal
        
    def hold(self, signalVal, t):
        timeInSample = t - self.timeStep
        if timeInSample >= self.samplTime: # New sample
            self.timeStep = t
            self.currVal = signalVal

        return self.currVal


class _dfilter:
    """
    Real-time digital filter
    
    """
    def __init__(self, filterNum, filterDen, bufferSize=16, initTime=0, initVal=0, samplTime=1):
        self.Num = filterNum
        self.Den = filterDen
        self.zi = _repMat( signal.lfilter_zi(filterNum, filterDen), 1, initVal.size)
        
        self.timeStep = initTime
        self.samplTime = samplTime
        self.buffer = _repMat(initVal, 1, bufferSize)
        
    def filt(self, signalVal, t=None):
        # Sample only if time is specified
        if t is not None:
            timeInSample = t - self.timeStep
            if timeInSample >= self.samplTime: # New sample
                self.timeStep = t
                self.buffer = _pushVec(self.buffer, signalVal)
        else:
            self.buffer = _pushVec(self.buffer, signalVal)
        
        bufferFiltered = np.zeros(self.buffer.shape)
        
        for k in range(0, signalVal.size):
                bufferFiltered[k,:], self.zi[k] = signal.lfilter(self.Num, self.Den, self.buffer[k,:], zi=self.zi[k, :])
        return bufferFiltered[-1,:]


class _pltMarker:
    """
    Robot marker for visualization
    
    """    
    def __init__(self, angle=None, pathString=None):
        self.angle = angle or []
        self.pathString = pathString or """m 66.893258,227.10128 h 5.37899 v 0.91881 h 1.65571 l 1e-5,-3.8513 3.68556,-1e-5 v -1.43933
        l -2.23863,10e-6 v -2.73937 l 5.379,-1e-5 v 2.73938 h -2.23862 v 1.43933 h 3.68556 v 8.60486 l -3.68556,1e-5 v 1.43158
        h 2.23862 v 2.73989 h -5.37899 l -1e-5,-2.73989 h 2.23863 v -1.43159 h -3.68556 v -3.8513 h -1.65573 l 1e-5,0.91881 h -5.379 z"""
        self.path = parse_path( self.pathString )
        self.path.vertices -= self.path.vertices.mean( axis=0 )
        self.marker = mpl.markers.MarkerStyle( marker=self.path)
        self.marker._transform = self.marker.get_transform().rotate_deg(angle)

    def rotate(self, angle=0):
        self.marker._transform = self.marker.get_transform().rotate_deg(angle-self.angle)
        self.angle = angle
    

# functions
def _toColVec(argin):
    if argin.ndim < 2:
        return np.reshape(argin, (argin.size, 1))
    elif argin.ndim ==2:
        if argin.shape[0] < argin.shape[1]:
            return argin.T
        else:
            return argin

def _repMat(argin, n, m):
    """
    Ensures 1D result
    
    """
    return np.squeeze(repmat(argin, n, m))

# def pushColRight(matrix, vec):
#     return np.hstack([matrix[:,1:], _toColVec(vec)])

def _pushVec(matrix, vec):
    return np.vstack([matrix[1:,:], vec])

def _uptria2vec(mat):
    """
    Convert upper triangular square sub-matrix to column vector
    
    """    
    n = mat.shape[0]
    
    vec = np.zeros( n*(n+1)/2, 1 )
    
    k = 0
    for i in range(n):
        for j in range(n):
            vec[j] = mat[i, j]
            k += 1