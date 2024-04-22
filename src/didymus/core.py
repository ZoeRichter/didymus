#imports
import numpy as np

class Core:
	'''
	Class for a single Core object, which will be referenced
	in packing and moving Pebble objects.  Contains only the
	information necessary to determine the core geometry and
	flow direction.
	'''
	def __init__(self,origin=np.zeros(3),downward_flow=True):
		'''
		Initializes a single instance of a Core object.  As
		this does not specify the shape of the core, the Core
		parent class should not be used directly.
		
		Parameters
        ----------
        origin : numpy array
		    A numpy array consisting of 3 elements: the x, y,
		    and z coordinates of the core's origin.  Default
		    is centered at (0.0,0.0,0.0)
		downward_flow : bool
		    Whether axial flow in the core is upward or downward.
		    True means flow is downward, False means it is upward.
		
		'''
		self.origin = origin
		self.downward_flow = downward_flow
	
class CylCore(Core):
	'''
	Class for a cylindrically shaped core, with its axis parallel
	to the z-axis.
	'''
	def __init__(self, core_r, core_h, *args, **kwargs):
		'''
		Initializes a single instance of a CylCore object.
		
		Parameters
        ----------
        core_r : float
		    Radius of the core.  Units must match other core
		    dimensions, including coordinates, and Pebble objects.
		core_h : float
			Height of the core.  Units must match other core
			dimensions, per core_r
		
		'''
		super().__init__(*args, **kwargs)
		self.core_r = core_r
		self.core_h = core_h
		
		
