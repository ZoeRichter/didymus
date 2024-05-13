#imports
import numpy as np
from collections import defaultdict
import didymus as di
from didymus import core
from didymus import pebble
rng = np.random.default_rng()

def pebble_packing(active_core, pebble_r, n_pebbles=0,n_mat_ids=0,pf=0,pf_mat_ids=0,k=10**(-3)):
	'''
	Function to pack pebbles into a cylindrical core (see the CylCore
	Class) using the Jodrey-Tory method.  Users must either define
	n_pebbles or pf, but not both, and describe the corresponding mat_id
	input argument (see below).  Packing function has an upper limit
	on packing fraction of 60%.
	
	Parameters
    ----------
    active_core : didymus CylCore object
		CylCore object defining the active core shape and flow
	pebble_r : float
		Pebble radius.  Units must match those in core
	n_pebbles : int
		Number of pebbles to be packed in core.  Either
		n_pebbles or pf must be defined, but not both
	n_mat_ids : numpy array
		numpy array containing the mat_ids of the pebbles.
		Only used if n_pebbles is defined.  Length must be
		equal to n_pebbles.
	pf : float
		Packing fraction of pebbles, in decimal form.  Either
		n_pebbles or pf must be defined, but not both.
	pf_mat_ids : dict
		Dictionary containing mat_id:weight key:value pairs,
		to be used with pf.  Weight describes the fraction of 
		total pebbles that will have the associated mat_id.  If 
		the weights do not perfectly divide among the number of
		generated pebbles, the choice of mat_id favors the pebbles
	    with greatest weight.
	k : float
	    Contraction rate, to be used with Jodrey-Tory
	    Algorithm
    
	'''
	
	assert n_pebbles != 0 or pf != 0, "n_pebbles or pf must be provided"
	assert not(n_pebbles != 0 and pf != 0), "only provide one of n_pebbles or pf"
	
	#add check to enforce a hard upper limit that pf <= 0.60
	assert pf <= 0.6, "pf must be less than or equal to 0.6"
	assert type(active_core) == di.core.CylCore, "Only CylCore is currently supported"
	
	if n_pebbles != 0 and pf == 0:
		assert type(n_mat_ids) == np.ndarray,"n_mat_ids must be a numpy array with length equal to n_pebbles"
		assert len(n_mat_ids) == n_pebbles,"n_mat_ids must be a numpy array with length equal to n_pebbles"
		pf = n_to_pf(active_core, pebble_r,n_pebbles)
		print("Equivalent packing fraction is " + str(pf))
		assert pf <= 0.6, "pf must be less than or equal to 0.6.  n_pebbles is too high."
		
	elif pf != 0 and n_pebbles == 0:
		assert pf_mat_ids != 0, "pf_mat_ids must be defined if using pf"
		assert type(pf_mat_ids) == dict, "pf_mat_ids must be a dictionary"
		n_pebbles = pf_to_n(active_core, pebble_r, pf)
		print("Equivalent number of pebbles is " + str(n_pebbles))
		
	#after assertions, just move forward with n_pebbles when you
	#find the starting coords
	init_coords = find_start_coords(active_core, pebble_r, n_pebbles)
	
	#now we actually get into the Jodrey-Tory algorithm, with the added
	#help of Rabin-Lipton method of probalisticaly solving the
	#nearest neighbor problem, so we're not brute-force searching for
	#the nearest neighbor.
	
	final_coords = jt_algorithm(active_core, pebble_r,init_coords,n_pebbles,k)
	
	return final_coords
	
		
def pf_to_n(active_core, pebble_r, pf):
	'''
	Converts packing fraction, pf, to number of pebbles, n_pebbles

    Parameters
    ----------
    active_core : didymus CylCore object
		didymus CylCore object defining pebble-filled region of the core.
    pebble_r : float
		Radius of a single pebble, with units matching those
		used to create center coordinates.
	pf : float
		Packing fraction, given in decimal format

    Returns
    ----------
    n_pebbles : int
		Number of pebbles in active core region
     
	'''
	if type(active_core) == di.core.CylCore:
		core_vol = (np.pi*(active_core.core_r**2))*active_core.core_h
		p_vol_tot = pf*core_vol
		p_vol = (4/3)*np.pi*pebble_r**3
		n_pebbles = np.floor(p_vol_tot/p_vol, dtype=int)
		return n_pebbles
		

def n_to_pf(active_core, pebble_r, n_pebbles):
	'''
	Converts number of pebbles to packing fraction
	
	Parameters
    ----------
    active_core : didymus CylCore object
		didymus CylCore object defining pebble-filled region of the core.
    pebble_r : float
		Radius of a single pebble, with units matching those
		used to create center coordinates.
	n_pebbles : int
		Number of pebbles in active core region

    Returns
    ----------
    pf : float
		Packing fraction, given in decimal format
	'''
	if type(active_core) == di.core.CylCore:
		core_vol = (np.pi*(active_core.core_r**2))*active_core.core_h
		p_vol = (4/3)*np.pi*pebble_r**3
		p_vol_tot = p_vol*n_pebbles
		pf = p_vol_tot/core_vol
		return pf


def find_start_coords(active_core, pebble_r, n_pebbles):
	'''
	Generates an array of starting center coordinates for pebble
	packing
	
	Parameters
    ----------
    active_core : didymus CylCore object
		didymus CylCore object defining pebble-filled region of the core.
    pebble_r : float
		Radius of a single pebble, with units matching those
		used to create center coordinates.
	n_pebbles : int
		Number of pebbles in active core region

    Returns
    ----------
    coords : float
		Numpy array of length n_pebbles, where each element is the centroid
		of a pebble
	'''
	
	#determine dimension upper and lower bounds
	z_up = active_core.origin[2] + 0.5*active_core.core_h - pebble_r -active_core.buff
	z_low = active_core.origin[2] -0.5*active_core.core_h + pebble_r + active_core.buff
	r_up = active_core.core_r - pebble_r -active_core.buff
	
	coords = np.empty(n_pebbles,dtype=np.ndarray)
	for i in range(n_pebbles):
		f = rng.random()
		theta = rng.uniform(0,2*np.pi)
		x = active_core.origin[0] + f*r_up*np.cos(theta)
		y = active_core.origin[1] + f*r_up*np.sin(theta)
		z = rng.uniform(z_low,z_up)
		coords[i] = np.array([x,y,z])
		
		
	return coords
	
def jt_algorithm(active_core, pebble_r,coords,n_pebbles,k):
	'''
	Performs the Jodrey-Tory algorithm (see: ***PUT DOI HERE***)
	to remove overlap from given pebble coords and return
	updated coords
	
	Parameters
    ----------
    active_core : didymus CylCore object
		didymus CylCore object defining pebble-filled region of the core.
    pebble_r : float
		Radius of a single pebble, with units matching those
		used to create center coordinates.
	coords : numpy array
		Numpy array of length n_pebbles, where each element is the centroid
		of a pebble.  This is pre-Jodrey-Tory.
	n_pebbles : int
		Number of pebbles in active core region
	k : float
		Contraction rate, used to determine the rate at which the outer,
		or nominal, diameter decreases in each iteration of the Jodrey-Tory
		algorithm.

    Returns
    ----------
    coords : float
		Numpy array of length n_pebbles, where each element is the centroid
		of a pebble.  This is post-Jodrey-Tory.
	'''
	
	#step 1: find initial d_out, which is d such that pf = 1
	if type(active_core) == di.core.CylCore:
		core_vol = (np.pi*(active_core.core_r**2))*active_core.core_h     
	d_out_0 = 2*np.cbrt((3*core_vol)/(4*np.pi*n_pebbles))
	d_out = d_out_0
	
	#step 2: probabilistic nearest neighbor search
	#to find worst overlap (shortest rod)
	
	#we can get the starting rod queue (and nearest neighbor)
	# with the nearest_neighbor function
	overlap = True
	i = 0
	while overlap:
		rod_queue = nearest_neighbor(active_core,pebble_r,coords,n_pebbles)
		if not rod_queue:
			overlap = False
			break
		else:
			for rod in rod_queue:
				d_in = min(rod_queue.values())
				p1 = rod[0]
				p2 = rod[1]
				coords[p1],coords[p2] = move(active_core,
										pebble_r,
										coords,
										rod,
										rod_queue[rod],
										d_out)
				if d_out < d_in:
					print('''Outer diameter and inner diameter converged too quickly.
					Try again with a smaller contraction rate.''')
					print("Maximum possible diameter with current packing:", d_in)
					overlap = False
					break
				del_pf = n_to_pf(active_core,d_out/2,n_pebbles)-n_to_pf(active_core,d_in/2,n_pebbles)
				j = np.floor(-np.log10(abs(del_pf)), dtype=int)
				d_out = d_out - (0.5**j)*(k/n_pebbles)*d_out_0
				i += 1
		if i > 10**8:
			overlap = False
			print("Did not reach packing fraction")
			print("Maximum possible pebble diameter with current packing is ", d_in)
	
	print(i)
	return coords
	
def nearest_neighbor(active_core, pebble_r, coords,n_pebbles):
	'''
	Performs Lipton-modified Rabin algorithm for the
	nearest neighbor search problem
	
	Parameters
    ----------
    active_core : didymus CylCore object
		didymus CylCore object defining pebble-filled region of the core.
    pebble_r : float
		Radius of a single pebble, with units matching those
		used to create center coordinates.
	coords : numpy array
		Numpy array of length n_pebbles, where each element is the centroid
		of a pebble.
	n_pebbles : int
		Number of pebbles in active core region

    Returns
    ----------
    rods : dict
		Dictionary with key:value pairs containing information on overlapping
		rods, to use with the Jodrey-Tory algorthim.  Each key is 2-element tuple
		in which each value is the index of the corresponding point in coords.
		The value is the distance (the length of the rod) between the two points
		defined by the key.
	'''
	
	init_pairs = {}
	for i in range(n_pebbles):
		p1, p2 = select_pair(coords,n_pebbles)
		while (p1,p2) in init_pairs:
			p1, p2 = select_pair(coords,n_pebbles)
		#frobenius norm is default
		init_pairs[(p1,p2)] = np.linalg.norm(coords[p1]-coords[p2])
	delta = min(init_pairs.values())
	
	mesh_id= meshgrid(active_core,coords,n_pebbles,delta)
	#now, for each grid square with at least one point (each element of mesh_id)
	#I make rods between each point in 
	#and all points in the moores neighborhood of that square (ix+/-1, iy+/-1, iz+/-1)
	rods = {}
	for i, msqr in enumerate(mesh_id.keys()):
		#checking x index:
		x_dict = defaultdict(list)
		for sqr in list(mesh_id.keys())[i:]:
			if sqr[0]<= msqr[0]+1 and sqr[0]>=msqr[0]-1:
				x_dict[sqr] = mesh_id[sqr]

		#now that we have all the potential grid spaces
		#with an x index in range (that weren't already caught in
		#a previous pass) we can use this subset and search for applicable y
		#we know x_dict can't be empty, because it at least as the
		#central mesh grid square in it (msqr)
		y_dict = defaultdict(list)
		for xsqr in list(x_dict.keys()):
			if xsqr[1] <= msqr[1]+1 and xsqr[1] >= msqr[1]-1:
				y_dict[xsqr] = mesh_id[xsqr]

		#repeat for z, using y_dict
		neighbors = []
		for ysqr in list(x_dict.keys()):
			if ysqr[2] <= msqr[2]+1 and ysqr[2] >= msqr[2]-1:
				neighbors += mesh_id[ysqr]
				
		#now, the list neighbors should include all points in
		#msqr, plus all points in squares adjacent to msqr -
		#but should skip over squares that would have been included
		# in a previous neighborhood
		#go through all points, brute-force calculate all rods
		#add rods to rods dict, then filter at very end
		for i, p1 in enumerate(neighbors):
			if i == n_pebbles-1:
				pass
			else:
				for p2 in neighbors[(i+1):]:
					if p1<p2:
						rods[(p1,p2)] = np.linalg.norm(coords[p1]-coords[p2])
					else:
						rods[(p2,p1)] = np.linalg.norm(coords[p1]-coords[p2])
	#now, we should have the unfiltered rod list.  but we don't really need all of these
	# we can immediately drop any rod longer than the diameter of a pebble (these pebs
	#aren't actually touching):
	pairs = list(rods.keys())
	for pair in pairs:
		if rods[pair] > 2*pebble_r:
			del rods[pair]
	#we also only move a given point relative to exactly one other point, prioritizing
	#the worst overlap (ie, the shortest rod)
	for p in range(n_pebbles):
		temp={}
		pairs = list(rods.keys())
		for pair in pairs:
			if pair[0] ==  p or pair[1] == p:
				temp[pair] = rods[pair]
		if not temp:
			pass
		else:
			temp_keys = list(temp.keys())
			for tkey in temp_keys:
				if temp[tkey] != min(temp.values()):
					del rods[tkey]
	return rods
		
def select_pair(coords,n_pebbles):
	'''
	select random pair of points from list of coords
	
	Parameters
    ----------
	coords : numpy array
		Numpy array of length n_pebbles, where each element is the centroid
		of a pebble.  This is pre-Jodrey-Tory.
	n_pebbles : int
		Total number of pebbles.

    Returns
    ----------
    p1, p2 : int
		Integers corresponding to the index of a point in coords,
		where p1 < p2.
	'''
	
	p1 = rng.integers(0,n_pebbles) #open on the upper end
	p2 = p1
	while p2 == p1:
		p2 = rng.integers(0,n_pebbles)
		
	if p1 > p2:
			p1, p2 = p2, p1
	return int(p1), int(p2)
	
def meshgrid(active_core,coords,n_pebbles,delta):
	'''
	determines what gamma lattice grid square each point in
	coords is in
	Parameters
    ----------
    active_core : didymus CylCore object
		didymus CylCore object defining pebble-filled region of the core.
	coords : numpy array
		Numpy array of length n_pebbles, where each element is the centroid
		of a pebble.  This is pre-Jodrey-Tory.
	n_pebbles : int
		Total number of pebbles
	delta : float
		From Rabin-Lipton nearest neighbor algorithm.  Delta is defined as
		the smallest distance between any of the initial, randomly-sampled
		pairs, and defines the side-length of the mesh grid square in 
		a lattice (Gamma) encompassing the active core region.

    Returns
    ----------
    mesh_index : dict
		Dictionary containg key:value pairs in which each key is a 3-element
		tuple containing the (ix, iy, iz) id code for a grid square in the gamma
		lattice, and the value is a list containing the specific points from
		coords that lie inside that grid square.
		
	'''
	
	
	Mx = np.ceil(active_core.core_r*2/delta, dtype=int)
	x_min = active_core.origin[0] - active_core.core_r
	My = np.ceil(active_core.core_r*2/delta, dtype=int)
	y_min = active_core.origin[1] - active_core.core_r
	Mz = np.ceil(active_core.core_h/delta, dtype=int)
	z_min = active_core.origin[2] - active_core.core_h/2
	fild_sqrs = np.empty(n_pebbles, dtype=object)
	for i, p in enumerate(coords):
		ix,iy,iz = None, None, None
		for j in range(Mx):
			if p[0] > (x_min + j*delta) and p[0] <= (x_min + (j+1)*delta):
				ix = j
				break
			else:
				if j == Mx-1:
					if not ix:
						ix = j
					else:
						pass
		for k in range(My):
			if p[1] > (y_min + k*delta) and p[1] <= (y_min + (k+1)*delta):
				iy = k
				break
			else:
				if k == My-1:
					if not iy:
						iy = k
					else:
						pass
		for l in range(Mz):
			if p[2] > (z_min + l*delta) and p[2] <= (z_min + (l+1)*delta):
				iz = l
				break
			else:
				if l == Mz-1:
					if not iz:
						iz = l
					else:
						pass
		fild_sqrs[i] = (ix,iy,iz)
	mesh_id = defaultdict(list)
	for i, v in enumerate(fild_sqrs):
		mesh_id[v].append(i)
		
		
	return mesh_id

def move(active_core,pebble_r, coords, pair, rod, d_out):
	'''
	moves the two points in rod so they are d_out apart
	
	Parameters
    ----------
    active_core : didymus CylCore object
		didymus CylCore object defining the active core region
	pebble_r : float
		Pebble radius, in units matching those in the core definition
	coords : numpy array
		Numpy array of length n_pebbles, where each element is the centroid
		of a pebble.  This is pre-Jodrey-Tory.
	pair : tuple
		A 2-element tuple made of integers, where each value corresponds
		to a point in coords
	rod : 
	n_pebbles : int
		Total number of pebbles.

    Returns
    ----------
    p1, p2 : int
		Integers corresponding to the index of a point in coords,
		where p1 < p2.
	'''
	l = (d_out-rod)/2
	p1, p2 = coords[pair[0]], coords[pair[1]]
	ux, uy, uz = (p1[0]-p2[0])/rod,(p1[1]-p2[1])/rod,(p1[2]-p2[2])/rod
	up1p2 = np.array([ux,uy,uz])
	
	z_up = active_core.origin[2] + 0.5*active_core.core_h - pebble_r -active_core.buff
	z_low = active_core.origin[2] -0.5*active_core.core_h + pebble_r +active_core.buff
	r_up = active_core.core_r - pebble_r -active_core.buff
	
	for i, p in enumerate(p1):
		p1[i] = p + up1p2[i]*l
		if i == 0: #x
			if abs(p1[i]) > active_core.origin[0]+r_up:
				theta = np.arctan(ux/uy)
				p1[i] = active_core.origin[0]+ r_up*np.cos(theta)
		if i == 1: #y
			if abs(p1[i]) > active_core.origin[1]+r_up:
				theta = np.arctan(ux/uy)
				p1[i] = active_core.origin[1]+ r_up*np.sin(theta)	
		else: #z
			if p1[i] > z_up:
				p1[i] = z_up
			elif p1[i] < z_low:
				p1[i] = z_low
				
	for i, p in enumerate(p2):
		p2[i] = p - up1p2[i]*l
		if i == 0: #x
			if abs(p2[i]) > r_up:
				theta = np.arctan(ux/uy)
				p2[i] = active_core.origin[0]-r_up*np.cos(theta)
		if i == 1: #y
			if abs(p2[i]) > r_up:
				theta = np.arctan(ux/uy)
				p2[i] = active_core.origin[1]-r_up*np.sin(theta)	
		else: #z
			if p2[i] > z_up:
				p2[i] = z_up
			elif p2[i] < z_low:
				p2[i] = z_low
		
	
	
	return p1,p2
	
