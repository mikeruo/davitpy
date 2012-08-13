# pydarn/radar/radFov.py
"""
*******************************
		radFov
*******************************
This module contains the following class:
	fov
		field of view position
		
This module contains the following functions
	slantRange
		Calculate slant range
	calcAzOffBore
		Calculate off-array-normal azimuth
	calcFieldPnt
		Calculate field point projection
	getFov
		calculate field of view coordinates

Based on Mike Ruohoniemi's GEOPACK
Based on R.J. Barnes radar.pro
Created by Sebastien
*******************************
"""

# *************************************************************
class fov(object):
	"""
This class stores field-of-view coordinates

See getFov documentation for details.
	"""
	def __init__(self, \
			frang=180.0, rsep=45.0, site=None, nbeams=None, ngates=None, bmsep=None, recrise=None, \
			elevation=None, altitude=300., \
			model='IS', coords='geo'):
		# Get fov
		radarDict = getFov(frang=frang, rsep=rsep, site=site, nbeams=nbeams, ngates=ngates, bmsep=bmsep, recrise=recrise, \
							elevation=elevation, altitude=altitude, model=model, coords=coords)
		if radarDict:
			self.latCenter = radarDict['latCenter']
			self.lonCenter = radarDict['lonCenter']
			self.latFull = radarDict['latFull']
			self.lonFull = radarDict['lonFull']
			self.slantRCenter = radarDict['slantRCenter']
			self.slantRFull = radarDict['slantRFull']
			self.beams = radarDict['beams']
			self.gates = radarDict['gates']
			self.coords = radarDict['coords']


# *************************************************************
def slantRange(frang, rsep, recrise, range_gate, center=True):
	"""srang = slantRange(frang, rsep, recrise, range_gate, center=True)
Calculate slant range

INPUTS:
	frang: first range gate position [km]
	rsep: range gate separation [km]
	recrise: receiver rise time [us]
	range_gate: range gate number(s)
	center: wether or not to compute the slant range in the center of the gate rather than at the edge
OUTPUT:
	srang: slant range [km]
	"""
	# Lag to first range gate [us]
	lagfr = frang * 2./0.3
	# Sample separation [us]
	smsep = rsep * 2./0.3
	# Range offset if calculating slant range at center of the gate
	range_offset = -0.5*rsep if center else 0.0
	
	# Slant range [km]
	srang = ( lagfr - recrise + (range_gate - 1.) * smsep ) * 0.3/2. + range_offset
	
	return srang


# *************************************************************
def calcAzOffBore(elevation, boreOffset0):
	"""boreOffset = calcAzOffBore(elevation, boreOffset0)
Calculate off-boresight azimuth as a function of elevation angle and zero-elevation off-boresight azimuth.
See Milan et al. [1997] for more details on how this works.

INPUTS:
	elevation: elevation angle [degree]
	boreOffset0: zero-elevation off-boresight azimuth [degree]
OUTPUT:
	boreOffset: off-boresight azimuth [degree]
	"""
	from math import radians, cos, sin, atan, pi, sqrt
	
	if ( cos(radians(boreOffset0))**2 - sin(radians(elevation))**2 ) < 0:
		if boreOffset0 >= 0: boreOffset = pi/2.
		else: boreOffset = -pi/2.
	else:
		tan_bOff = sqrt( sin(radians(boreOffset0))**2 / ( cos(radians(boreOffset0))**2 - sin(radians(elevation))**2 ) )
		if boreOffset0 >= 0: boreOffset0 = atan( tan_bOff )
		else: boreOffset = -atan( tan_bOff )
		
	return boreOffset

		
# *************************************************************
def calcFieldPnt(tGeoLat, tGeoLon, tAlt, boreSight, boreOffset, slantRange, elevation=None, altitude=None, model=None):
	"""lat, lon = calcFieldPnt(tGeoLat, tGeoLon, boreSight, boreOffset, slantRange, elevation=None, altitude=None)
Calculate coordinates of field point given the radar coordinates and boresight, the pointing direction 
deviation from boresight and elevation angle, and the field point slant range and altitude.
Either the elevation or the altitude must be provided. If none is provided, the altitude is 
set to 300 km and the elevation evaluated to accomodate altitude and range.

INPUTS:
	tGeoLat: transmitter latitude [degree, N]
	tGeoLon: transmitter longitude [degree, E]
	tAlt: transmitter altitude [km]
	boreSight: boresight azimuth [degree, E]
	boreOffset: offset from boresight [degree]
	slantRange: slant range [km]
	elevation: elevation angle [degree] (estimated if None)
	altitude: altitude [km] (default 300 km)
	model: 
		'IS': for ionopsheric scatter projection model
		'GS': for ground scatter projection model
		None: if you are really confident in your elevation or altitude data
		... more to come
OUTPUT:
	lat: latitude of field point [degree]
	lon: longitude of field point [degree]
	"""
	from math import radians, degrees, sin, cos, asin, atan, sqrt, pi
	from utils import Re, geoPack
	
	# Make sure we have enough input stuff
	if (not model) and (not elevation or not altitude):
		print 'calcFieldPnt: if using none of the projection models, you need to provide elevation or altitude. Setting IS model'
		model = 'IS'
	
	# Now let's get to work
	# Classis Ionospheric/Ground scatter projection model
	if model in ['IS','GS']:
		# Make sure you have altitude, because these 2 projection models rely on it
		if not elevation and not altitude:
			# Set default altitude to 300 km
			altitude = 300.0
		elif elevation and not altitude:
			# If you have elevation but not altitude, then you calculate altitude, and elevation will be adjusted anyway
			altitude = sqrt( Re**2 + slantRange**2 + 2. * slantRange * Re * sin( radians(elevation) ) ) - Re
		
		# Now you should have altitude (and maybe elevation too, but it won't be used in the rest of the algorithm)
		# Adjust altitude so that it makes sense with common scatter distribution
		xAlt = altitude
		if model == 'IS':
			if altitude > 150. and slantRange <= 600: 
				xAlt = 115.
			elif altitude > 150. and slantRange > 600. and  slantRange <= 800.:
				xAlt = 115. + ( slantRange - 600. ) / 200. * ( altitude - 115. )
		elif model == 'GS':
			if altitude > 150. and slantRange <= 300: 
				xAlt = 115.
			elif altitude > 150. and slantRange > 300. and  slantRange <= 500.:
				xAlt = 115. + ( slantRange - 300. ) / 200. * ( altitude - 115. )
		if slantRange < 150.: xAlt = slantRange / 150. * 115.
		
		# To start, set Earth radius below field point to Earth radius at radar
		(lat,lon,tRe) = geoPack.geodToGeoc(tGeoLat,tGeoLat,into='geoc')
		RePos = tRe
		
		# Iterate until the altitude corresponding to the calculated elevation matches the desired altitude
		n = 0L # safety counter
		while True:
			# pointing elevation (spherical Earth value) [degree]
			tel = degrees( asin( ((RePos+xAlt)**2 - tRe**2 - slantRange**2) / (2. * tRe * slantRange) ) )
			
			# estimate off-array-normal azimuth (because it varies slightly with elevation) [degree]
			bOff = calcAzOffBore(tel, boreOffset)
			
			# pointing azimuth
			taz = boreSight + bOff
			print n, tel, taz, RePos
			
			# calculate position of field point
			dictOut = geoPack.calcDistPnt(tGeoLat, tGeoLon, tAlt, dist=slantRange, el=tel, az=taz)
			
			# Update Earth radius 
			RePos = dictOut['distRe']
			
			# stop if the altitude is what we want it to be (or close enough)
			if abs(xAlt - dictOut['distAlt']) <= 0.5: 
				return dictOut['distLat'], dictOut['distLon']
				break
			print '-----------------', RePos, xAlt, dictOut['distAlt'], dictOut['distLat'], dictOut['distLon']
			n += 1L
			if n > 3: 
				return dictOut['distLat'], dictOut['distLon']
				break
			
	
	# No projection model (i.e., the elevation or altitude is so good that it gives you the proper projection by simple geometric considerations)
	elif not model:
		# Using no models simply means tracing based on trustworthy elevation or altitude
		if not elevation:
			altitude = sqrt( Re**2 + slantRange**2 + 2. * slantRange * Re * sin( radians(elevation) ) ) - Re
		# The tracing is done by calcDistPnt
		dict = calcDistPnt(tGeoLat, tGeoLon, tAlt, dist=slantRange, el=elevation, az=boreSight+boreOffset, distAlt=altitude)
		return dict['distLat'], dict['distLon']
		


# *************************************************************
def getFov(frang=180.0, rsep=45.0, site=None, nbeams=None, ngates=None, bmsep=None, recrise=None, elevation=None, altitude=None, model=None, coords='geo'):
	"""radarFovDict = getFov(frang=180.0, rsep=45.0, site=None, nbeams=None, ngates=None, bmsep=None, recrise=None, elevation=None, altitude=None, model=None, coords='geo')
Calculate field of view coordinates. Provide the input-set [nbeams, ngates, bmsep, recrise] or a SITE object. Parameters from the
input-set will always take precedence over parameters from the SITE object.
Make sure to provide frang and rsep, the default values are not always applicable.

INPUTS:
	site: site structure for a given radar and date-time
	frang: first range gate position [km] (defaults to 180 km) (scalar or ndarray(nbeams))
	rsep: range gate separation [km] (defaults to 45 km) (scalar or ndarray(nbeams))
	nbeams: number of beams (use site information if not provided)
	ngates: number of gates (use site information if not provided)
	bmsep: beam separation [degree] (use site information if not provided)
	recrise: receiver rise time [us] (use site information if not provided) (scalar or ndarray(nbeams))
	elevation: elevation angle [degree] (if not provided, is evaluated using 'model') (scalar or ndarray(ngates) or ndarray(nbeams,ngates))
	altitude: altitude [km] (if not provided, set to 300 km) (scalar or ndarray(ngates) or ndarray(nbeams,ngates))
	model: 
		'IS': for ionopsheric scatter projection model (default)
		'GS': for ground scatter projection model
		None: if you are really confident in your elevation or altitude values
		... more to come
	coords: 'geo' (more to come)
OUTPUT:
	radarFovDict: dictionary with the following keys:
		latCenter: latitude at center of a range gate [degree]
		lonCenter: longitude at center of a range gate [degree]
		slantRCenter: slant range associated with each range gate center [km]
		latFull: latitude at 4 corners of a range gate [degree]
		lonFull: longitude at 4 corners of a range gate [degree]
		slantRFull: slant range associated with each range gate 4 corners [km]
		beams: the beam numbers for which positions are calculated
		gates: the gate number for which positions are calculated
		coords: projection coordinates
	"""
	from numpy import ndarray, array, arange, zeros
	
	# Test that we have enough input arguments to work with
	if not site and None in [nbeams, ngates, bmsep, recrise]:
		print 'calcFov: must provide either a site object or [nbeams, ngates, bmsep, recrise].'
		return
		
	# Then assign variables from the site object if necessary
	if site:
		if not nbeams: nbeams = site.maxbeam
		if not ngates: ngates = site.maxgate
		if not bmsep: bmsep = site.bmsep
		if not recrise: recrise = site.recrise
		
	# Some type checking. Look out for arrays
	# If frang, rsep or recrise are arrays, then they should be of shape (nbeams,)
	# Set a flag if any of frang, rsep or recrise is an array
	isParamArray = False
	if isinstance(frang, ndarray):
		isParamArray = True
		if len(frang) != nbeams: 
			print 'getFov: frang must be of a scalar or ndarray(nbeams). Using first element: {}'.format(frang[0])
			frang = frang[0] * ones(nbeams+1)
		# Array is adjusted to add on extra beam edge by copying the last element
		else: frang = np.append(frang, frang[-1])
	else: frang = array([frang])
	if isinstance(rsep, ndarray):
		isParamArray = True
		if len(rsep) != nbeams: 
			print 'getFov: rsep must be of a scalar or ndarray(nbeams). Using first element: {}'.format(rsep[0])
			rsep = rsep[0] * ones(nbeams+1)
		# Array is adjusted to add on extra beam edge by copying the last element
		else: rsep = np.append(rsep, rsep[-1])
	else: rsep = array([rsep])
	if isinstance(recrise, ndarray):
		isParamArray = True
		if len(recrise) != nbeams: 
			print 'getFov: recrise must be of a scalar or ndarray(nbeams). Using first element: {}'.format(recrise[0])
			recrise = recrise[0] * ones(nbeams+1)
		# Array is adjusted to add on extra beam edge by copying the last element
		else: recrise = np.append(recrise, recrise[-1])
	else: recrise = array([recrise])
	
	# If altitude or elevation are arrays, then they should be of shape (nbeams,ngates)
	if isinstance(altitude, ndarray):
		if altitude.ndim == 1:
			if altitude.size != ngates:
				print 'getFov: altitude must be of a scalar or ndarray(ngates) or ndarray(nbeans,ngates). Using first element: {}'.format(altitude[0])
				altitude = altitude[0] * ones((nbeams+1, ngates+1))
			# Array is adjusted to add on extra beam/gate edge by copying the last element and replicating the whole array as many times as beams
			else: altitude = np.resize( np.append(altitude, altitude[-1]), (nbeams+1,ngates+1) )
		elif altitude.ndim == 2:
			if altitude.shape != (nbeams, ngates):
				print 'getFov: altitude must be of a scalar or ndarray(ngates) or ndarray(nbeans,ngates). Using first element: {}'.format(altitude[0])
				altitude = altitude[0] * ones((nbeams+1, ngates+1))
			# Array is adjusted to add on extra beam/gate edge by copying the last row and column
			else: 
				altitude = np.append(altitude, altitude[-1,:].reshaphe(1,ngates), axis=0)
				altitude = np.append(altitude, altitude[:,-1].reshaphe(nbeams,1), axis=1)
		else:
			print 'getFov: altitude must be of a scalar or ndarray(ngates) or ndarray(nbeans,ngates). Using first element: {}'.format(altitude[0])
			altitude = altitude[0] * ones((nbeams+1, ngates+1))
	if isinstance(elevation, ndarray):
		if elevation.ndim == 1:
			if elevation.size != ngates:
				print 'getFov: elevation must be of a scalar or ndarray(ngates) or ndarray(nbeans,ngates). Using first element: {}'.format(elevation[0])
				elevation = elevation[0] * ones((nbeams+1, ngates+1))
			# Array is adjusted to add on extra beam/gate edge by copying the last element and replicating the whole array as many times as beams
			else: elevation = np.resize( np.append(elevation, elevation[-1]), (nbeams+1,ngates+1) )
		elif elevation.ndim == 2:
			if elevation.shape != (nbeams, ngates):
				print 'getFov: elevation must be of a scalar or ndarray(ngates) or ndarray(nbeans,ngates). Using first element: {}'.format(elevation[0])
				elevation = elevation[0] * ones((nbeams+1, ngates+1))
			# Array is adjusted to add on extra beam/gate edge by copying the last row and column
			else: 
				elevation = np.append(elevation, elevation[-1,:].reshaphe(1,ngates), axis=0)
				elevation = np.append(elevation, elevation[:,-1].reshaphe(nbeams,1), axis=1)
		else:
			print 'getFov: elevation must be of a scalar or ndarray(ngates) or ndarray(nbeans,ngates). Using first element: {}'.format(elevation[0])
			elevation = elevation[0] * ones((nbeams+1, ngates+1))
	
	# Generate beam/gate arrays
	beams = arange(nbeams+1)
	gates = arange(ngates+1)
	
	# Create output arrays
	slantRangeFull = zeros((nbeams+1, ngates+1, 4), dtype='float')
	latFull = zeros((nbeams+1, ngates+1, 4), dtype='float')
	lonFull = zeros((nbeams+1, ngates+1, 4), dtype='float')
	slantRangeCenter = zeros((nbeams+1, ngates+1), dtype='float')
	latCenter = zeros((nbeams+1, ngates+1), dtype='float')
	lonCenter = zeros((nbeams+1, ngates+1), dtype='float')
	
	# Iterates through beams
	for ib in beams:
		# if none of frang, rsep or recrise are arrays, then only execute this for the first loop, otherwise, repeat for every beam
		if (~isParamArray and ib == 0) or isParamArray:
			# Calculate center slant range
			sRangCenter = slantRange(frang[ib], rsep[ib], recrise[ib], gates, center=True)
			# Calculate edges slant range
			sRangEdge = slantRange(frang[ib], rsep[ib], recrise[ib], gates, center=False)
		# Save into output arrays
		slantRangeCenter[ib, :-1] = sRangCenter[:-1]
		slantRangeFull[ib, :-1, 0] = sRangEdge[:-1]
		slantRangeFull[ib, :-1, 1] = sRangEdge[:-1]
		slantRangeFull[ib, :-1, 2] = sRangEdge[1:]
		slantRangeFull[ib, :-1, 3] = sRangEdge[1:]
	
		# Calculate deviation from boresight for center of beam
		bOffCenter = bmsep * (ib - nbeams/2.0 + 0.5)
		# Calculate deviation from boresight for edge of beam
		bOffEdge = bmsep * (ib - nbeams/2.0)
		
		# Calculate coordinates for Edge and Center of the current beam
		for ig in gates:
			print ib, ig, sRangCenter[ig]
			# This is a bit redundant, but I could not think of any other way to deal with the array-or-not-array issue
			if not isinstance(altitude, ndarray) and not isinstance(elevation, ndarray):
				print bOffCenter
				latC, lonC = calcFieldPnt(site.geolat, site.geolon, site.alt, bOffCenter, site.boresite, sRangCenter[ig], \
							elevation=elevation, altitude=altitude, model=model)
				print bOffEdge
				latE, lonE = calcFieldPnt(site.geolat, site.geolon, site.alt, bOffEdge, site.boresite, sRangEdge[ig], \
							elevation=elevation, altitude=altitude, model=model)
			elif isinstance(altitude, ndarray) and not isinstance(elevation, ndarray):
				latC, lonC = calcFieldPnt(site.geolat, site.geolon, site.alt, bOffCenter, site.boresite, sRangCenter[ig], \
							elevation=elevation, altitude=altitude[ib,ir], model=model)
				latE, lonE = calcFieldPnt(site.geolat, site.geolon, site.alt, bOffEdge, site.boresite, sRangEdge[ig], \
							elevation=elevation, altitude=altitude[ib,ir], model=model)
			elif isinstance(elevation, ndarray) and not isinstance(altitude, ndarray):
				latC, lonC = calcFieldPnt(site.geolat, site.geolon, site.alt, bOffCenter, site.boresite, sRangCenter[ig], \
							elevation=elevation[ib,ir], altitude=altitude, model=model)
				latE, lonE = calcFieldPnt(site.geolat, site.geolon, site.alt, bOffEdge, site.boresite, sRangEdge[ig], \
							elevation=elevation[ib,ir], altitude=altitude, model=model)
			else:
				latC, lonC = calcFieldPnt(site.geolat, site.geolon, site.alt, bOffCenter, site.boresite, sRangCenter[ig], \
							elevation=elevation[ib,ir], altitude=altitude[ib,ir], model=model)
				latE, lonE = calcFieldPnt(site.geolat, site.geolon, site.alt, bOffEdge, site.boresite, sRangEdge[ig], \
							elevation=elevation[ib,ir], altitude=altitude[ib,ir], model=model)
			# Save into output arrays
			latCenter[ib, ig] = latC
			lonCenter[ib, ig] = lonC
			latFull[ib, ig, 0] = latE
			lonFull[ib, ig, 0] = lonE
			if ig > 0: 
				latFull[ib, ig-1, 3] = latE
				lonFull[ib, ig-1, 3] = lonE
			if ib > 0: 
				latFull[ib-1, ig, 1] = latE
				lonFull[ib-1, ig, 1] = lonE
			if ib > 0 and ig > 0:
				latFull[ib-1, ig-1, 2] = latE
				lonFull[ib-1, ig-1, 2] = lonE
	
	# Output is...
	radarFovDict = {'latCenter': latCenter[:-1,:-1], \
		'lonCenter': lonCenter[:-1,:-1], \
		'slantRCenter': slantRangeCenter[:-1,:-1], \
		'latFull': latFull[:-1,:-1,:], \
		'lonFull': lonFull[:-1,:-1,:], \
		'slantRFull': slantRangeFull[:-1,:-1,:], \
		'beams': beams[:-1], \
		'gates': gates[:-1], \
		'coords': coords}
	
	return radarFovDict