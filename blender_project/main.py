import bpy
import bpy_types
import bpy_extras
import numpy
import math
from math import e, pi
import itertools
import os
import sys
import random
import bmesh
from functools import reduce

#The path to the this source file
filepath = os.path.dirname(os.path.abspath(__file__))
#print (filepath)
sys.path.insert(0, filepath)
#filepath = filepath[0:filepath.rfind("/") + 1]

from entity import Entity
from geometry_utils import *
from parser import *

#filepath = "/u/gplatono/BlenderProjects/SRP/objects/"
#import geometry_utils
link = False
#The current scene
scene = bpy.context.scene

#List of the relation names
relation_list = ['near',
                 'in',
                 'on' ,
                 'touching',
                 'front',
                 'behind',
                 'right',
                 'left',
                 'at',
                 'over',
                 'under',
                 'above',
                 'below',
                 'between']

#List of  possible color modifiers
color_mods = ['black', 'red', 'blue', 'brown', 'green', 'yellow']

types = []

types_ids = {
    'chair':  'props.item.furniture.chair',
    'table':  'props.item.furniture.table',    
    'bed':     'props.item.furniture.bed',
    'sofa':  'props.item.furniture.sofa',
    'bookshelf':  'props.item.furniture.bookshelf',
    'desk':  'props.item.furniture.desk',
    'book': 'props.item.portable.book',
    'laptop': 'props.item.portable.laptop',
    'pencil': 'props.item.portable.pencil',
    'pencil holder': 'props.item.portable.pencil holder',
    'note': 'props.item.portable.note',
    'rose': 'props.item.portable.rose',
    'vase': 'props.item.portable.vase',
    'cardbox': 'props.item.portable.cardbox',
    'box': 'props.item.portable.box',
    'ceiling light': 'props.item.stationary.ceiling light',
    'lamp': 'props.item.portable.lamp',
    'apple': 'props.item.food.apple',
    'banana': 'props.item.food.banana',
    'plate': 'props.item.portable.plate',
    'bowl': 'props.item.portable.bowl',
    'recycle bin': 'props.item.portable.recycle bin',
    'tv': 'props.item.appliances.tv',
    'poster': 'props.item.stationary.poster',
    'picture': 'props.item.stationary.picture',
    'fridge' : 'props.item.appliances.fridge',
    'ceiling fan': 'props.item.stationary.ceiling fan',
    'block': 'props.item.block',
    'floor': 'world.plane.floor',
    'ceiling': 'world.plane.ceiling',
    'wall': 'world.plane.wall'
}
    
#Dictionary that maps the relation names to the names of the functions that implement them
rf_mapping = {'to the left of': 'to_the_left_of_deic',
              'to the right of': 'to_the_right_of_deic',
              'near': 'near',
              'on': 'on',
              'above': 'above',
              'below': 'below',
              'over': 'over',
              'under': 'under',
              'in': 'inside',
              'touching': 'touching',
              'right': 'to_the_right_of_deic',
              'left': 'to_the_left_of_deic',
              'at': 'at',
              'in front of': 'in_front_of_deic',
              'front': 'in_front_of_deic',
              'behind': 'behind_deic',
              'between': 'between'}

#The list of entities
entities = []

#The observer object (camera)
observer = None

#Average distance between entities in the scene
avg_dist = 0

#
#OBSOLETE CODE (WILL BE REMOVED LATER)
#
def match_pattern(pattern, input_list):
	#print (pattern, input_list)
    for i in range(len(pattern)):
        if (pattern[i] != input_list[i]):
            return False
    return True

def get_types():
	ret_val = []
	for entity in entities:
		if entity.get_type_structure() is not None:
			for elem in entity.get_type_structure():
				if elem not in ret_val:
					ret_val.append(elem)
	return ret_val

class Token:
	def __init__(self, token):
		self.token = token

	def readable(self):
		return self.token

class Argument(Token):
	def __init__(self, argument, color_mod=None):
		super().__init__(argument)
		self.argument = argument
		self.color_mod = color_mod

	def readable(self):
		return [self.color_mod.readable(), self.token] if self.color_mod is not None else self.token

class Relation(Token):
	def __init__(self, relation, relatum=None, referent_list=None, entity_list=None):
		super().__init__(relation)
		self.relation = relation
		self.relatum = relatum
		if referent_list is None:
			self.referent_list = []
		self.entity_list = entity_list

	def readable(self):
		return [self.token, self.relatum, [ref.readable() for ref in self.referent_list]]

class Mod(Token):
	def __init__(self, mod_type, value):
		super().__init__(value)
		self.mod_type = mod_type
		self.value = value

def parse_response(response):
	parse_stack = []
	for word in response.split():
		if word in relation_list:
			parse_stack.append(Relation(word))
		elif word in color_mods:
			parse_stack.append(Mod('color_mod', word))
		elif word in types:
			arg = Argument(word)
			if len(parse_stack) > 0 and type(parse_stack[-1]) is Mod:
				arg.color_mod = parse_stack.pop()
			if len(parse_stack) > 0 and type(parse_stack[-1]) is Relation:
				parse_stack[-1].referent_list.append(arg)
			else:
				parse_stack.append(arg)
	return parse_stack

def dist_obj(a, b):
    if type(a) is not Entity or type(b) is not Entity:
        return -1
    bbox_a = a.get_bbox()
    bbox_b = b.get_bbox()
    center_a = a.get_bbox_centroid()
    center_b = b.get_bbox_centroid()
    if a.get('extended') is not None:
        return a.get_closest_face_distance(center_b)
    if b.get('extended') is not None:
        return b.get_closest_face_distance(center_a)
    return point_distance(center_a, center_b)

#END OF THE OBSOLETE SEGMENT



#Computes the value of the univariate Gaussian
#Inputs: x - random variable value; mu - mean; sigma - variance
#Return value: real number
def gaussian(x, mu, sigma):
    return e ** (- 0.5 * ((float(x) - mu) / sigma) ** 2) / (math.fabs(sigma) * math.sqrt(2.0 * pi))

#Computes the value of the logistic sigmoid function
#Inputs: x - random variable value; a, b - coefficients
#Return value: real number
def sigmoid(x, a, b):
    return a / (1 + e ** (- b * x)) if b * x > -100 else 0


#Computes the normalized area of the intersection of projection of two entities onto the XY-plane
#Inputs: a, b - entities
#Return value: real number
def get_proj_intersection(a, b):
    bbox_a = a.get_bbox()
    bbox_b = b.get_bbox()
    axmin = bbox_a[0][0]
    axmax = bbox_a[7][0]
    aymin = bbox_a[0][1]
    aymax = bbox_a[7][1]
    bxmin = bbox_b[0][0]
    bxmax = bbox_b[7][0]
    bymin = bbox_b[0][1]
    bymax = bbox_b[7][1]
    dim1 = max(axmax, bxmax) - min(axmin, bxmin) - (axmax - axmin + bxmax - bxmin)
    dim2 = max(aymax, bymax) - min(aymin, bymin) - (aymax - aymin + bymax - bymin)
    area = math.fabs(dim1 * dim2)
    if dim1 >= 0 or dim2 >= 0:
        area = -area
    #Normalize the intersection area to [0, 1]
    return e ** ((area - min((axmax - axmin) * (aymax - aymin), (bxmax - bxmin) * (bymax - bymin))) / 
                    min((axmax - axmin) * (aymax - aymin), (bxmax - bxmin) * (bymax - bymin)))


#Returns the orientation of the entity relative to the coordinate axes
#Inputs: a - entity
#Return value: triple representing the coordinates of the orientation vector
def get_planar_orientation(a):
    dims = a.get_dimensions()
    if dims[0] == min(dims):
        return (1, 0, 0)
    elif dims[1] == min(dims):
        return (0, 1, 0)
    else: return (0, 0, 1)


#Returns the frame size of the current scene
#Inputs: none
#Return value: real number
def get_frame_size():
    max_x = -100
    min_x = 100
    max_y = -100
    min_y = 100
    max_z = -100
    min_z = 100

    #Computes the scene bounding box
    for entity in entities:
        max_x = max(max_x, entity.span[1])
        min_x = min(min_x, entity.span[0])
        max_y = max(max_y, entity.span[3])
        min_y = min(min_y, entity.span[2])
        max_z = max(max_z, entity.span[5])
        min_z = min(min_z, entity.span[4])
    return max(max_x - min_x, max_y - min_y, max_z - min_z)


#Raw metric for the nearness relation
#Doesn't take into account the nearness statistics in the scene
#Inputs: a, b - entities
#Return value: real number from [0, 1], the raw nearness measure
def near_raw(a, b):
    bbox_a = a.get_bbox()
    bbox_b = b.get_bbox()
    dist = dist_obj(a, b)
    #print(dist)
    max_dim_a = max(bbox_a[7][0] - bbox_a[0][0],
                    bbox_a[7][1] - bbox_a[0][1],
                    bbox_a[7][2] - bbox_a[0][2])
    max_dim_b = max(bbox_b[7][0] - bbox_b[0][0],
                    bbox_b[7][1] - bbox_b[0][1],
                    bbox_b[7][2] - bbox_b[0][2])
    if a.get('planar') is not None:
        dist = min(dist, get_planar_distance_scaled(a, b))
    elif b.get('planar') is not None:
        dist = min(dist, get_planar_distance_scaled(b, a))
        #print ("PLANAR DIST: ", dist)
    elif a.get('vertical_rod') is not None or a.get('horizontal_rod') is not None or a.get('rod') is not None:
        dist = min(dist, get_line_distance_scaled(a, b))
    elif b.get('vertical_rod') is not None or b.get('horizontal_rod') is not None or b.get('rod') is not None:
        dist = min(dist, get_line_distance_scaled(b, a))
    elif a.get('concave') is not None or b.get('concave') is not None:
        dist = min(dist, closest_mesh_distance_scaled(a, b))

    fr_size = get_frame_size()
    #print ("FR_SIZE", fr_size)
    raw_metric = e ** (-0.05 * dist)
    '''0.5 * (1 - min(1, dist / avg_dist + 0.01) +'''    
    return raw_metric * (1 - raw_metric / fr_size)

#Computes the nearness measure for two entities
#Takes into account the scene statistics:
#The raw nearness score is updated depending on whether one object is the closest to another
#Inputs: a, b - entities
#Return value: real number from [0, 1], the nearness measure
def near(a, b):
    raw_near_a = []
    raw_near_b = []
    raw_near_measure = near_raw(a, b)
    for entity in entities:
        if entity != a and entity != b:
            near_a_entity = near_raw(a, entity)
            near_b_entity = near_raw(b, entity)
            #print (entity.name, near_a_entity, near_b_entity)
            #if dist_a_to_entity < raw_dist:
            raw_near_a += [near_a_entity]
            #if dist_b_to_entity < raw_dist:
            raw_near_b += [near_b_entity]
    #print ("RAW:", raw_near_measure)
    average_near_a = sum(raw_near_a) / len(raw_near_a)
    average_near_b = sum(raw_near_b) / len(raw_near_b)
    #print ("AVER: ", average_near_a, average_near_b)
    near_measure = raw_near_measure + (raw_near_measure - (average_near_a + average_near_b) / 2) * (1 - raw_near_measure)
    #print (near_measure)
    return near_measure

#Computes the between relation (a is between b and c)
#Inputs: a, b, c - entities
#Return value: real number from [0, 1]
def between(a, b, c):
    bbox_a = a.get_bbox()
    bbox_b = a.get_bbox()
    bbox_c = c.get_bbox()
    center_a = a.get_bbox_centroid()
    center_b = b.get_bbox_centroid()
    center_c = c.get_bbox_centroid()
    dist = get_distance_from_line(center_b, center_c, center_a) / max(max(a.dimensions), max(b.dimensions), max(c.dimensions))
    #max_dim_a = max(bbox_a[7][0] - bbox_a[0][0],
    #                bbox_a[7][1] - bbox_a[0][1],
    #                bbox_a[7][2] - bbox_a[0][2])
    
    return dist


#Computes the degree of vertical alignment (coaxiality) between two entities
#The vertical alignment takes the max value if one of the objects is directly above the other
#Inputs: a, b - entities
#Return value: real number from [0, 1]
def v_align(a, b):
    dim_a = a.get_dimensions()
    dim_b = b.get_dimensions()
    center_a = a.get_bbox_centroid()
    center_b = b.get_bbox_centroid()
    return gaussian(0.9 * point_distance((center_a[0], center_a[1], 0), (center_b[0], center_b[1], 0)) / 
                                (max(dim_a[0], dim_a[1]) + max(dim_b[0], dim_b[1])), 0, 1 / math.sqrt(2*pi))

#Computes the degree of vertical offset between two entities
#The vertical offset measures how far apart are two entities one
#of which is above the other. Takes the maximum value when one is
#directly on top of another
#Inputs: a, b - entities
#Return value: real number from [0, 1]
def v_offset(a, b):
    dim_a = a.get_dimensions()    
    dim_b = b.get_dimensions()
    center_a = a.get_bbox_centroid()
    center_b = b.get_bbox_centroid()
    h_dist = math.sqrt((center_a[0] - center_b[0]) ** 2 + (center_a[1] - center_b[1]) ** 2)    
    return gaussian(2 * (center_a[2] - center_b[2] - 0.5*(dim_a[2] + dim_b[2])) /  \
                    (1e-6 + dim_a[2] + dim_b[2]), 0, 1 / math.sqrt(2*pi))

#Computes the "larger-than" relation
#Inputs: a, b - entities
#Return value: real number from [0, 0.5]
def larger_than(a, b):
    bbox_a = a.get_bbox()
    bbox_b = b.get_bbox()
    return 1 / (1 + e ** (bbox_b[7][0] - bbox_b[0][0] \
                          + bbox_b[7][1] - bbox_b[0][1] \
                          + bbox_b[7][2] - bbox_b[0][2] \
                          - (bbox_a[7][0] - bbox_a[0][0] \
                             + bbox_a[7][1] - bbox_a[0][1] \
                             + bbox_a[7][2] - bbox_a[0][2])))


#Computes the "on" relation
#Inputs: a, b - entities
#Return value: real number from [0, 1]
def on(a, b):
    ret_val = 0.5 * (v_offset(a, b) + get_proj_intersection(a, b))
    ret_val = max(ret_val, 0.5 * (above(a, b) + touching(a, b)))
    for ob in b.constituents:
        if ob.get('working_surface') is not None or ob.get('planar') is not None:
            ret_val = max(ret_val, 0.5 * (v_offset(a, ob) + get_proj_intersection(a, ob)))
            ret_val = max(ret_val, 0.5 * (int(near(a, ob) > 0.99) + larger_than(ob, a)))
    if b.get('planar') is not None and isVertical(b):
        ret_val = max(ret_val, math.exp(- 0.5 * get_planar_distance_scaled(a, b)))
    #if b.get('planar') is not None :
    #    ret_val = max(ret_val, )
    #if ret_val >= 0.6:
    #    return 0.5 * (ret_val + larger_than(b, a))
    return ret_val

#Computes the "over" relation
#Currently, the motivation behind the model is that
#one object is considered to be over the other
#iff it's above it and relatively close to it.
#Inputs: a, b - entities
#Return value: real number from [0, 1]
def over(a, b):
    bbox_a = a.get_bbox()
    bbox_b = b.get_bbox()
    return 0.5 * above(a, b) + 0.2 * get_proj_intersection(a, b) + 0.3 * near(a, b)


#Computes the "under" relation, which is taken to be symmetric to "over"
#Inputs: a, b - entities
#Return value: real number from [0, 1]
def under(a, b):
    return over(b, a)


#Computes the "closer-than" relation
#Inputs: a, b - entities
#Return value: real number from [0, 1]
def closer_than(a, b, pivot):
    return 1 if point_distance(a.get_bbox(), pivot.get_bbox()) < point_distance(b.get_bbox(), pivot.get_bbox()) else 0


#Computes the deictic version of the "in-front-of" relation
#For two objects, one is in front of another iff it's closer and
#between the observer and that other object
#Inputs: a, b - entities
#Return value: real number from [0, 1]
def in_front_of_deic(a, b):
#def in_front_of_extr(a, b, observer):
    bbox_a = a.get_bbox()
    max_dim_a = max(bbox_a[7][0] - bbox_a[0][0],
                    bbox_a[7][1] - bbox_a[0][1],
                    bbox_a[7][2] - bbox_a[0][2]) + 0.0001
    dist = get_distance_from_line(observer.get_centroid(), b.get_bbox_centroid(), a.get_bbox_centroid())
    return 0.5 * (closer_than(a, b, observer) + e ** (-dist / max_dim_a))

#Enable SVA
#Computes the deictic version of the "behind" relation
#which is taken to be symmetric to "in-front-of"
#Inputs: a, b - entities
#Return value: real number from [0, 1]
def behind_deic(a, b):
    return in_front_of_deic(b, a)

'''
def bbox_inside_test(a, b):
    shared_volume = get_bbox_intersection(a, b)
    return shared_volume / (b.dimensions[0] * b.dimensions[1] * b.dimensions[2] + 0.001)
'''

#Computes the "at" relation
#Inputs: a, b - entities
#Return value: real number from [0, 1]
def at(a, b):
    return 0.8 * near(a, b) + 0.2 * touching(a, b)

relations = {}

#The following functions are for precomputing the corresponding
#relation for every pair of entities
#
#

def compute_at(entities):
    obj = [[x, [y for y in entities if x != y and near(y, x) > 0.8]] for x in entities]
    return "\n".join(", ".join(y.name for y in x[1]) + " is at the " + x[0].name for x in obj if x[1] != [])

def compute_near(entities):
    obj = [[x, [y for y in entities if x != y and near(y, x) > 0.6]] for x in entities]
    return "\n".join(", ".join(y.name for y in x[1]) + " is near the " + x[0].name for x in obj if x[1] != [])

def compute_on(entities):
    obj = [[x, [y for y in entities if x != y and on(y, x) > 0.8]] for x in entities]
    return "\n".join(", ".join(y.name for y in x[1]) + " is on the " + x[0].name for x in obj if x[1] != [])

def compute_above(entities):
    obj = [[x, [y for y in entities if x != y and above(y, x) > 0.7]] for x in entities]
    return "\n".join(", ".join(y.name for y in x[1]) + " is above the " + x[0].name for x in obj if x[1] != [])

def compute_below(entities):
    obj = [[x, [y for y in entities if x != y and below(y, x) > 0.7]] for x in entities]
    return "\n".join(", ".join(y.name for y in x[1]) + " is below the " + x[0].name for x in obj if x[1] != [])

def compute_over(entities):
    obj = [[x, [y for y in entities if x != y and over(y, x) > 0.7]] for x in entities]
    return "\n".join(", ".join(y.name for y in x[1]) + " is over the " + x[0].name for x in obj if x[1] != [])

#

'''
def gen_data(func_name):
    pos = 100.0
    neg = 100.0
    data = open(func_name + ".train", "w")
    index = 0
    for pair in itertools.permutations(entities, r = 2):
        if index < 1000:
            a, b = pair
            if a.name != 'plane' and b.name != 'plane':
                a_bbox_str = " ".join([" ".join([str(x) for x in y]) for y in a.get_bbox()])
                b_bbox_str = " ".join([" ".join([str(x) for x in y]) for y in b.get_bbox()])
                a_cen = a.get_bbox_centroid()
                b_cen = b.get_bbox_centroid()
                outstr = a_bbox_str + " " + b_bbox_str #" ".join([str(x) for x in a_cen]) + " " + " ".join([str(x) for x in b_cen])            
                if globals()[func_name](a, b) > 0.7: # and float(pos) / (pos + neg) <= 0.6:
                    outstr = outstr + " 1\n"
                    #pos = pos + 1
                    data.write(outstr)
                else: #if neg / (pos + neg) <= 0.6:
                    outstr = outstr + " -1\n"
                    #neg = neg + 1
                    data.write(outstr)
                index = index + 1
    data.close()
''' 

#Creates and configures the special "observer" object
#(which is just a camera). Needed for deictic relations as
#well as several other aspects requiring the POV concept,
#e.g., taking screenshots.
#Inputs: none
#Return value: the camera object
def get_observer():
    lamp = bpy.data.lamps.new("Lamp", type = 'POINT')
    lamp.energy = 30
    cam = bpy.data.cameras.new("Camera")

    if bpy.data.objects.get("Lamp") is not None:
        lamp_obj = bpy.data.objects["Lamp"]
    else:
        lamp_obj = bpy.data.objects.new("Lamp", lamp)
        scene.objects.link(lamp_obj)
    if bpy.data.objects.get("Camera") is not None:
        cam_ob = bpy.data.objects["Camera"]
    else:
        cam_ob = bpy.data.objects.new("Camera", cam)
        scene.objects.link(cam_ob)    

    lamp_obj.location = (-20, 0, 10)
    cam_ob.location = (-15.5, 0, 7)
    cam_ob.rotation_mode = 'XYZ'
    cam_ob.rotation_euler = (1.1, 0, -1.57)
    bpy.data.cameras['Camera'].lens = 20
    
    bpy.context.scene.camera = scene.objects["Camera"]


    mesh = bpy.data.meshes.new("observer")
    #scene.objects.active = obj
    #obj.select = True
    mesh = bpy.context.object.data
    bm = bmesh.new()
    #print (cam_ob.location)
    bm.verts.new(cam_ob.location)
    bm.to_mesh(mesh)
    observer = bpy.data.objects.new("Observer", mesh)
    scene.objects.link(observer)
    bm.free()
    scene.update()
    observer_entity = Entity(observer)
    observer_entity.camera = cam_ob
    return observer_entity

#Searches and returns the entity that has the given name
#associated with it
#Inputs: name - human-readable name as a string
#Return value: entity (if exists) or None
def get_entity_by_name(name):
    for entity in entities:
        #print(name, entity.name)
        if entity.name.lower() == name.lower():
            return entity
    for col in color_mods:
        if col in name:
            name = name.replace(col + " ", "")
            #print ("MOD NAME:", name)
    for entity in entities:
        #print(name, entity.name)
        if entity.name.lower() == name.lower():
            return entity
    return None

#Places the entity at a specified location and with specified orientation
#Inputs: entity, position - triple of point coordinates, rotation - triple of Euler angles
#Return value: none
def place_entity(entity, position=(0,0,0), rotation=(0,0,0)):
    obj = entity.constituents[0]
    obj.location = position
    obj.rotation_mode = 'XYZ'
    obj.rotation_euler = rotation
    scene.update()

#Places the set of entities within a certain region 
#Inputs: reg - the bounding box of the region, collection - list of entities
#Return value: none
def arrange_entities(reg, collection):
    for entity in collection:
        if entity.get('fixed') is None:
            #print (entity.name)
            if reg[4] == reg[5]:
                pos = (random.uniform(reg[0], reg[1]), random.uniform(reg[2], reg[3]), reg[4])#entity.get_parent_offset()[2])
            else:
                pos = (random.uniform(reg[0], reg[1]), random.uniform(reg[2], reg[3]), random.uniform(reg[4], reg[5]))
            place_entity(entity, pos, (math.pi,0,0))
            while check_collisions(entity):
                print (entity.name, pos)
                if reg[4] == reg[5]:
                    pos = (random.uniform(reg[0], reg[1]), random.uniform(reg[2], reg[3]), reg[4])#entity.get_parent_offset()[2])
                else:
                    pos = (random.uniform(reg[0], reg[1]), random.uniform(reg[2], reg[3]), random.uniform(reg[4], reg[5]))
                place_entity(entity, pos, (math.pi,0,0))

#Checks if the projections of two entities onto a coordinate axis "collide" (overlap)
#Inputs: int_a, int_b - the projections of two entities as intervals (pairs of numbers)
#Return value: Boolean value                
def axis_collision(int_a, int_b):
    return int_a[1] <= int_b[1] and int_a[1] >= int_b[0] or \
int_a[0] >= int_b[0] and int_a[0] <= int_b[1] or \
int_b[0] >= int_a[0] and int_b[0] <= int_a[1] or \
int_b[1] >= int_a[0] and int_b[1] <= int_a[1]

#Checks if the entity "collides" (overlaps) with some other entity along any coordinate axis
#Inputs: a - entity
#Return value: Boolean value                
def check_collisions(a):
    for entity in entities:
        if entity != a and check_collision(a, entity):
            print (entity.name, a.name)
            return True
    return False            

#Checks if two entities "collide" (overlap) along some coordinate axis
#Inputs: a,b - entities
#Return value: Boolean value                
def check_collision(a, b):
    span_a = a.get_span()
    span_b = b.get_span()
    return axis_collision((span_a[0], span_a[1]), (span_b[0], span_b[1])) and \
                          axis_collision((span_a[2], span_a[3]), (span_b[2], span_b[3])) and \
                          axis_collision((span_a[4], span_a[5]), (span_b[4], span_b[5]))

#STUB
def put_on_top(a, b):
    pass


#Render and save the current scene screenshot
#Inputs: none
#Return value: none
def save_screenshot():
    add_props()
    scene.render.resolution_x = 1920
    scene.render.resolution_y = 1080
    scene.render.resolution_percentage = 100
    scene.render.use_border = False
    scene.render.image_settings.file_format = 'JPEG'
    current_scene = bpy.data.filepath.split("/")[-1].split(".")[0]
    scene.render.filepath = filepath + current_scene + ".jpg"
    bpy.ops.render.render(write_still=True)

#Given the relations argument specification, returns the entities that
#satisfy that specification
#Inputs: arg - argument object
#Return value: the list of entities
def get_argument_entities(arg):
    #print ("ARG = ", arg, ";", arg.token,";", arg.mod.det,";", arg.mod.adj)
    ret_val = [get_entity_by_name(arg.token)]
    #print ("RET_VAL:", ret_val)
    if ret_val == [None]:
        ret_val = []
        #if arg.mod != None and arg.mod.det == 'a':
            #print (entities)
        for entity in entities:
            #print ("ENTITY_ARG: ", arg.token, entity.name, entity.get_type_structure(), entity.color_mod)
            if (entity.type_structure is None):
                print ("NONE STRUCTURE", entity.name)
            if (arg.token in entity.type_structure or arg.token in entity.name.lower() or arg.token == "block" and "cube" in entity.type_structure) \
               and (arg.mod.adj == "" or arg.mod.adj is None or entity.color_mod == arg.mod.adj):
                ret_val += [entity]
    #print ("REFER RETVAL: ", ret_val) 
    return ret_val

#Computes the projection of an entity onto the observer's visual plane
#Inputs: entity - entity, observer - object, representing observer's position
#and orientation
#Return value: list of pixel coordinates in the observer's plane if vision
def vp_project(entity, observer):
    points = reduce((lambda x,y: x + y), [[obj.matrix_world * v.co for v in obj.data.vertices] for obj in entity.constituents if (obj is not None and hasattr(obj.data, 'vertices') and hasattr(obj, 'matrix_world'))])
    #print (points)
    co_2d = [bpy_extras.object_utils.world_to_camera_view(scene, observer.camera, point) for point in points]
    render_scale = scene.render.resolution_percentage / 100
    render_size = (int(scene.render.resolution_x * render_scale), int(scene.render.resolution_y * render_scale),)
    pixel_coords = [(round(point.x * render_size[0]),round(point.y * render_size[1]),) for point in co_2d]
    return pixel_coords

#Computes the "touching" relation
#Two entities are touching each other if they
#are "very close"
#Inputs: a, b - entities
#Return value: real number from [0, 1]
def touching(a, b):
    bbox_a = a.get_bbox()
    bbox_b = b.get_bbox()
    center_a = a.get_bbox_centroid()
    center_b = b.get_bbox_centroid()
    rad_a = max(bbox_a[7][0] - bbox_a[0][0], \
                bbox_a[7][1] - bbox_a[0][1], \
                bbox_a[7][2] - bbox_a[0][2]) / 2
    rad_b = max(bbox_b[7][0] - bbox_b[0][0], \
                bbox_b[7][1] - bbox_b[0][1], \
                bbox_b[7][2] - bbox_b[0][2]) / 2
    
    #if a.name == "Apple 1" and b.name == "Bowl":
    #print (center_a, center_b)

    for point in bbox_a:
	#if a.name == "Apple 1" and b.name == "Bowl":
	#print (point_distance(point, center_b))i
        if point_distance(point, center_b) < rad_b:
            return 1
    for point in bbox_b:
        if point_distance(point, center_a) < rad_a:
            return 1
    mesh_dist = 1e9
    #print ("CENTROID DIST:" , get_centroid_distance_scaled(a, b))
    if get_centroid_distance_scaled(a, b) <= 0.8:
        mesh_dist = closest_mesh_distance_scaled(a, b)
    return math.exp(- 5 * mesh_dist)

#Filters the entities list according to the set of constraints, i.e.,
#returns the list of entities satisfying certain criteria
#Inputs: entities - list of entities; constaints - list of constraints in the
#form (type, value), e.g., (color_mod, 'black')
#Return value: list of entities
def filter(entities, constraints):
    result = []
    #print ("COLOR_MOD", constraints[1][1])
    #print ("FILTER:", entities, constraints)
    for entity in entities:
        isPass = True
        #print ("ENT_COLOR_MOD", entity.color_mod)
        for cons in constraints:
            #print("TYPE_STR:", entity.name, entity.get_type_structure())
            if cons[0] == 'type' and entity.get_type_structure()[-2] != cons[1]:
                isPass = False
            elif cons[0] == 'color_mod' and entity.color_mod != cons[1]:
                isPass = False
        if isPass:
            result.append(entity)
    return result


#For a description task, finds the best candiadate entity
#Inputs: relation - relation name (string), rel_constraints - the list of constraints
#imposed on the relatum, referents - the list of referent entities
#Return value: the best candidate entity
def eval_find(relation, rel_constraints, referents):
    candidates = filter(entities, rel_constraints)
    #print ("CAND:", candidates)
    scores = []
    if relation != "between":
        #print("SCORES:", relation, referents)
        scores = [(cand, cand.name, sum([globals()[rf_mapping[relation]](cand, ref) for ref in referents])) for cand in candidates]
        print(scores)
    else:
        return None ####FIX THIS LATER!!!
    #for sc in scores:
    #    print ("CAND:", sc[1], sc[2])
    max_score = 0
    best_candidate = None
    for ev in scores:
        if ev[2] > max_score:
            max_score = ev[2]
            best_candidate = ev[0]
    return best_candidate

#Processes a truth-judgement annotation
#Inputs: relation, relatum, referent1, referent2 - strings, representing
#the relation and its arguments; response - user's response for the test
#Return value: the value of the corresponding relation function
def process_truthjudg(relation, relatum, referent1, referent2, response):
    #print (relation, relatum, referent1, referent2, response)
    relatum = get_entity_by_name(relatum)
    referent1 = get_entity_by_name(referent1)
    referent2 = get_entity_by_name(referent2)
    print (relatum, referent1, referent2)
    if relation != "between":
        return globals()[rf_mapping[relation]](relatum, referent1)
    else: return globals()[rf_mapping[relation]](relatum, referent1, referent2)

#Extracts the constraints (type and color) for the relatum argument
#from the parsing result.
#Inputs: relatum - string, representing the relation argument;
#rel_constraints - the type and color properties of the relatum
#Return value: The list of pairs ('constraint_name', 'constraint_value')
def get_relatum_constraints(relatum, rel_constraints):
    print ("RELATUM TYPE:", relatum.get_type_structure()[-2])
    ret_val = [('type', relatum.get_type_structure()[-2]), ('color_mod', relatum.color_mod)]
    return ret_val

#Processes a description-tast annotation
#Inputs: relatum - string, representing the relation argument;
#response - user's response for the test
#Return value: the best-candidate entity fo the given description
def process_descr(relatum, response):
    rel_constraint = parse(response)
    print ("REL_CONST:", rel_constraint, rel_constraint.referents[0].mod)
    print ("RELATUM:", relatum)
    relatum = get_entity_by_name(relatum)
    print ("RELATUM:", relatum.name)
    print ("RESPONSE:", response)
    refs = []
    if rel_constraint is None:
        return "*RESULT: NO RELATIONS*"
    for ref in rel_constraint.referents:
        print (ref.token)
    refs += get_argument_entities(ref)
    #print ("REFERENTS:", [ref.name for ref in refs])
    relation = rel_constraint.token
    #for entity in entities:
    #    if entity.name == "Table" and bpy.data.objects.get("Camera") is not None:
    #        print (proj(entity.constituents[0], bpy.data.objects["Camera"]))
    return eval_find(relation, get_relatum_constraints(relatum, rel_constraint), refs)

def scaled_axial_distance(a_bbox, b_bbox):
    a_span = (a_bbox[1] - a_bbox[0], a_bbox[3] - a_bbox[2])
    b_span = (b_bbox[1] - b_bbox[0], b_bbox[3] - b_bbox[2])
    a_center = ((a_bbox[0] + a_bbox[1]) / 2, (a_bbox[2] + a_bbox[3]) / 2)
    b_center = ((b_bbox[0] + b_bbox[1]) / 2, (b_bbox[2] + b_bbox[3]) / 2)
    axis_dist = (a_center[0] - b_center[0], a_center[1] - b_center[1])
    return (2 * axis_dist[0] / max(a_span[0] + b_span[0], 2), 2 * axis_dist[1] / max(a_span[1] + b_span[1], 2))

def get_weighted_measure(a, b, observer):
    a_bbox = get_2d_bbox(vp_project(a, observer))
    b_bbox = get_2d_bbox(vp_project(b, observer))
    axial_dist = scaled_axial_distance(a_bbox, b_bbox)
    if axial_dist[0] <= 0:
        return 0
    horizontal_component = sigmoid(axial_dist[0], 1.0, 0.5) - 0.5
    vertical_component = gaussian(axial_dist[1], 0, 2.0)
    distance_factor = math.exp(-0.01 * axial_dist[0])
    return 0.5 * horizontal_component + 0.3 * vertical_component + 0.2 * distance_factor

#Computes a special function that takes a maximum value at cutoff point
#and decreasing to zero with linear speed to the left, and with exponetial speed to the right
#Inputs: x - position; cutoff - maximum point; left, right - degradation coeeficients for left and
#right sides of the function
#Return value: real number from [0, 1]
def asym_inv_exp(x, cutoff, left, right):
    return math.exp(- right * (x - cutoff)**2) if x >= cutoff else max(0, left * (x/cutoff) ** 3)

#Symmetric to the asym_inv_exp.
#Computes a special function that takes a maximum value at cutoff point
#and decreasing to zero with linear speed to the RIGHT, and with exponetial speed to the LEFT
#Inputs: x - position; cutoff - maximum point; left, right - degradation coeeficients for left and
#right sides of the function
#Return value: real number from [0, 1]
def asym_inv_exp_left(x, cutoff, left, right):
    return math.exp(- left * (x - cutoff)**2) if x < cutoff else max(0, right * (x/cutoff) ** 3)

#Computes the deictic version of to-the-right-of relation
#Inputs: a, b - entities
#Return value: real number from [0, 1]
def to_the_right_of_deic(a, b):
    a_bbox = get_2d_bbox(vp_project(a, observer))
    b_bbox = get_2d_bbox(vp_project(b, observer))
    axial_dist = scaled_axial_distance(a_bbox, b_bbox)
    if axial_dist[0] <= 0:
        return 0
    horizontal_component = asym_inv_exp(axial_dist[0], 1, 1, 0.1)#sigmoid(axial_dist[0], 2.0, 5.0) - 1.0
    vertical_component = math.exp(- 1.2 * axial_dist[1]**2)
    distance_factor = math.exp(- 0.1 * axial_dist[0])
    print ("Hor:", horizontal_component, "VERT:", vertical_component, "DIST:", distance_factor)
    weighted_measure = 0.5 * horizontal_component + 0.5 * vertical_component# + 0.2 * distance_factor
    return weighted_measure
        #for entity in entities:
        #    if entity != a and entity != b:

#Computes the deictic version of to-the-left-of relation
#Inputs: a, b - entities
#Return value: real number from [0, 1]
def to_the_left_of_deic(a, b):
    return to_the_right_of_deic(b, a)

#Computes the above relation
#Inputs: a, b - entities
#Return value: real number from [0, 1]
def above(a, b):
    bbox_a = a.get_bbox()
    bbox_b = b.get_bbox()
    span_a = a.get_span()
    span_b = b.get_span()
    center_a = a.get_bbox_centroid()
    center_b = b.get_bbox_centroid()
    scaled_vertical_distance = (center_a[2] - center_b[2]) / ((span_a[5] - span_a[4]) + (span_b[5] - span_b[4]))
    return 0.33333 * (max(int(bbox_a[0][2] > bbox_b[7][2]), e ** (- math.fabs(bbox_a[0][2] - bbox_b[7][2]))) + sigmoid(5 * (center_a[2] - center_b[2]) / (0.01 + bbox_a[7][2] - bbox_a[0][2] + bbox_b[7][2] - bbox_b[0][2]), 1, 1) + get_proj_intersection(a, b))

#Computes the below relation, which is taken to be symmetric to above
#Inputs: a, b - entities
#Return value: real number from [0, 1]
def below(a, b):
    return above(b, a)

#STUB
def in_front_of_intr(a, b):
    pass

#STUB
def behind_intr(a, b):
    in_front_of_intr(b, a)


def fix_ids():
    for ob in scene.objects:
        if ob.get('main') is not None:# and ob.get('id') is None:
            for key in types_ids.keys():
                if key in ob.name.lower():
                    ob['id'] = types_ids[key] + "." + ob.name
                    
#Entry point
#Implements the evaluation pipeline
def main():
    for obj in scene.objects:
        if obj.get('main') is not None:
            entities.append(Entity(obj))
    global avg_dist
    if len(entities) != 0:
        for pair in itertools.combinations(entities, r = 2):
            avg_dist += dist_obj(pair[0], pair[1])
        avg_dist = avg_dist * 2 / (len(entities) * (len(entities) - 1))

    global observer
    observer = get_observer()
    if "--" in sys.argv:
        args = sys.argv[sys.argv.index("--") + 1:]
        init_parser([entity.name for entity in entities])
        if len(args) != 6:
            result = "*RESULT: MALFORMED*"
        else:
            relation = args[0].lower()
            relatum = args[1].lower()
            referent1 = args[2].lower()
            referent2 = args[3].lower()
            task_type = args[4].lower()
            response = args[5].lower()
            print ("ANNOTATION PARAMS:", task_type, relatum, relation, referent1, referent2, response)
        
            if task_type == "1":
                best_cand = process_descr(relatum, response)
                if best_cand != None:
                    print(process_descr(relatum, response).name, "==?", relatum)
                print("RESULT:", get_entity_by_name(relatum) == best_cand)
            else:
                print("RESULT:", process_truthjudg(relation, relatum, referent1, referent2, response))
        return

    
    bl4 = get_entity_by_name("Block 4")
    bl9 = get_entity_by_name("Block 9")
    #pict = get_entity_by_name("Picture 1")
    #pen = get_entity_by_name("Black Pencil")
    print (bl4.name, bl9.name)
    print (touching(bl9, bl4))
    #print(vp_project(entities[0], observer))    
    #picture 2 red chair 1#print (entities[5].name, entities[0].name)
    '''for entity1 in entities:
        for entity2 in entities:
            if entity1.name != entity2.name:
                print (entity1.name, entity2.name)
                print ("RIGHT:", to_the_right_of_deic(entity1, entity2, observer))
                print ("LEFT:", to_the_left_of_deic(entity1, entity2, observer))'''

if __name__ == "__main__":
    # save_screenshot()
    #fix_ids()
    #print (bpy.data.filepath)
    #bpy.ops.wm.save_mainfile(filepath=bpy.data.filepath)
    main()
