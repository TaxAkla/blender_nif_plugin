#!BPY

""" Registration info for Blender menus:
Name: 'NetImmerse/Gamebryo (.nif & .kf)...'
Blender: 240
Group: 'Import'
Tip: 'Import NIF File Format (.nif & .kf)'
"""

__author__ = "Alessandro Garosi (AKA Brandano) -- tdo_brandano@hotmail.com"
__url__ = ("blender", "elysiun", "http://niftools.sourceforge.net/")
__version__ = "1.3"
__bpydoc__ = """\
This script imports Netimmerse (the version used by Morrowind) .NIF files to Blender.
So far the script has been tested with 4.0.0.2 format files (Morrowind, Freedom Force).
There is a know issue with the import of .NIF files that have an armature; the file will import, but the meshes will be somewhat misaligned.

Usage:

Run this script from "File->Import" menu and then select the desired NIF file.

Options:

Scale Correction: How many NIF units is one Blender unit?

Vertex Duplication (Fast): Fast but imperfect: may introduce unwanted cracks in UV seams.

Vertex Duplication (Slow): Perfect but slow, this is the preferred method if the model you are importing is not too large.

Smoothing Flag (Slow): Import seams and convert them to "the Blender way", is slow and imperfect, unless model was created by Blender and had no duplicate vertices.

Tex Path: Semi-colon separated list of texture directories.
"""

# nif_import.py version 1.3
# --------------------------------------------------------------------------
# ***** BEGIN LICENSE BLOCK *****
# 
# BSD License
# 
# Copyright (c) 2005, NIF File Format Library and Tools
# All rights reserved.
# 
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
# 1. Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
# 3. The name of the NIF File Format Library and Tools project may not be
#    used to endorse or promote products derived from this software
#    without specific prior written permission.
# 
# THIS SOFTWARE IS PROVIDED BY THE AUTHOR ``AS IS'' AND ANY EXPRESS OR
# IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES
# OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED.
# IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT
# NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF
# THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
# ***** END LICENCE BLOCK *****
# Note: Versions of this script previous to 1.0.6 were released under the GPL license
# The script includes small portions of code obtained in the public domain, in particular
# the binary conversion functions. Every attempt to contact (or actually identify!) the
# original author has so far been fruitless.
# I have no claim of ownership these functions and will remove and replace them with
# a (probably less efficient) version if the original author ever will ask me to.
# --------------------------------------------------------------------------
#
# Credits:
# Portions of this programs are (were) derived (through the old tested method of cut'n paste)
# from the obj import script obj_import.py: OBJ Import v0.9 by Campbell Barton (AKA Ideasman)
# (No more. I rewrote the lot. Nevertheless I wouldn't have been able to start this without Ideasman's
# script to read from!)
# Binary conversion functions are courtesy of SJH. Couldn't find the full name, and couldn't find any
# license info, I got the code for these from http://projects.blender.org/pipermail/bf-python/2004-July/001676.html
# The file reading strategy was 'inspired' by the NifToPoly script included with the 
# DAOC mapper, which used to be available at http://www.randomly.org/projects/mapper/ and was written and 
# is copyright 2002 of Oliver Jowett. His domain and e-mail address are however no longer reacheable.
# No part of the original code is included here, as I pretty much rewrote everything, hence this is the 
# only mention of the original copyright. An updated version of the script is included with the DAOC Mappergui
# application, available at http://nathrach.republicofnewhome.org/mappergui.html
#
# Thanks go to:
# Campbell Barton (AKA Ideasman, Cambo) for making code clear enough to be used as a learning resource.
#   Hey, this is my first ever python script!
# SJH for the binary conversion functions. Got the code off a forum somewhere, posted by Ideasman,
#   I suppose it's allright to use it
# Lars Rinde (AKA Taharez), for helping me a lot with the file format, and with some debugging even
#   though he doesn't 'do Python'
# Timothy Wakeham (AKA timmeh), for taking some of his time to help me get to terms with the way
#   the UV maps work in Blender
# Amorilia (don't know your name buddy), for bugfixes and testing.



# Using the same setup as for Amorilia's exporter, so that the configuration can be shared, and to try
# sticking a little better to conventions
try:
    import types, re
except:
    err = """--------------------------
ERROR\nThis script requires a full Python 2.4 installation to run.
--------------------------""" % sys.version
    print err
    Draw.PupMenu("ERROR%t|Python installation not found, check console for details")
    raise

import Blender, sys
from Blender import BGL
from Blender import Draw
from Blender.Mathutils import *

try:
    from niflib import *
except:
    err = """--------------------------
ERROR\nThis script requires the NIFLIB Python SWIG wrapper, niflib.py & _niflib.dll.
Make sure these files reside in your Python path or in your Blender scripts folder.
If you don't have them: http://niftools.sourceforge.net/
--------------------------"""
    print err
    Blender.Draw.PupMenu("ERROR%t|NIFLIB not found, check console for details")
    raise

# leave this, just in case we don't need a full Python installation in future for the SWIG wrapper
enableRe = 1
##try:
##    import re
##except:
##    err = """--------------------------
##ERROR\nThis script relies on the Regular Expression (re) module for some functionality.
##advanced texture lookup will be disabled
##--------------------------"""
##    print err
##    Blender.Draw.PupMenu("RE not found, check console for details")
##    enableRe = 0


# dictionary of texture files, to reuse textures
global textures
textures = {}

# dictionary of materials, to reuse materials
global materials
materials = {}

# Regex to handle replacement texture files
if enableRe:
    re_dds = re.compile(r'^\.dds$', re.IGNORECASE)
    re_dds_subst = re.compile(r'^\.(tga|png|jpg|bmp|gif)$', re.IGNORECASE)
    
# some variables

USE_GUI = 0 # BROKEN, don't set to 1, we will design a GUI for importer & exporter jointly
EPSILON = 0.005 # used for checking equality with floats, NOT STORED IN CONFIG

# 
# Process config files.
# 

global gui_texpath, gui_scale, gui_last

# configuration default values
TEXTURES_DIR = 'C:\\Program Files\\Bethesda\\Morrowind\\Data Files\\Textures' # Morrowind: this will work on a standard installation
IMPORT_DIR = ''
SEAMS_IMPORT = 1

# tooltips
tooltips = {
    'TEXTURES_DIR': "Texture directory.",
    'IMPORT_DIR': "Default import directory.",
    'SEAMS_IMPORT': "How to handle seams?"
}

# bounds
limits = {
    'SEAMS_IMPORT': [0, 2]
}

# update registry
def update_registry():
    # populate a dict with current config values:
    d = {}
    d['TEXTURES_DIR'] = TEXTURES_DIR
    d['IMPORT_DIR'] = IMPORT_DIR
    d['SEAMS_IMPORT'] = SEAMS_IMPORT
    d['tooltips'] = tooltips
    d['limits'] = limits
    # store the key
    Blender.Registry.SetKey('nif_import', d, True)
    read_registry()

# Now we check if our key is available in the Registry or file system:
def read_registry():
    global TEXTURES_DIR, IMPORT_DIR, SEAMS_IMPORT
    
    regdict = Blender.Registry.GetKey('nif_import', True)
    # If this key already exists, update config variables with its values:
    if regdict:
        try:
            TEXTURES_DIR = regdict['TEXTURES_DIR'] 
            IMPORT_DIR = regdict['IMPORT_DIR']
            SEAMS_IMPORT = regdict['SEAMS_IMPORT']
        # if data was corrupted (or a new version of the script changed
        # (expanded, removed, renamed) the config vars and users may have
        # the old config file around):
        except: update_registry() # rewrite it
    else: # if the key doesn't exist yet, use our function to create it:
        update_registry()

read_registry()



# check export script config key for scale correction

SCALE_CORRECTION = 10.0 # same default value as in export script

rd = Blender.Registry.GetKey('nif_export', True)
if rd:
    try:
        SCALE_CORRECTION = rd['SCALE_CORRECTION']
    except: pass

# check General scripts config key for default behaviors

VERBOSE = True
CONFIRM_OVERWRITE = True

rd = Blender.Registry.GetKey('General', True)
if rd:
    try:
        VERBOSE = rd['verbose']
        CONFIRM_OVERWRITE = rd['confirm_overwrite']
    except: pass

# Little wrapper for debug messages
def msg(message='-', level=2):
    if VERBOSE:
        print message

#
# A simple custom exception class.
#
class NIFImportError(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)


#
# Emulates the act of pressing the "home" key
#
def fit_view():
    Draw.Redraw(1)
    winid = Blender.Window.GetScreenInfo(Blender.Window.Types.VIEW3D)[0]['id']
    Blender.Window.SetKeyQualifiers(0)
    Blender.Window.QAdd(winid, Draw.HOMEKEY, 1)
    Blender.Window.QHandle(winid)
    Blender.Window.QAdd(winid, Draw.HOMEKEY, 0)
    Draw.Redraw(1)
    
#
# Main import function.
#
def import_nif(filename):
    try: # catch NIFImportErrors
        global NIF_DIR, TEX_DIR
        NIF_DIR = Blender.sys.dirname(filename)
        # Morrowind smart texture dir
        idx = NIF_DIR.lower().find('meshes')
        if ( idx >= 0 ):
            TEX_DIR = NIF_DIR[:idx] + 'textures'
        else:
            TEX_DIR = None
        # scene info
        global b_scene
        b_scene = Blender.Scene.GetCurrent()
        # read the NIF file
        root_block = ReadNifTree(filename)
        # used to control the progress bar
        global block_count, blocks_read, read_progress
        block_count = BlocksInMemory()
        read_progress = 0.0
        blocks_read = 0.0
        blocks = root_block["Children"].asLinkList()
        for niBlock in blocks:
            b_obj = read_branch(niBlock)
            if b_obj:
                b_obj.setMatrix(b_obj.getMatrix() * fb_scale_mat())
        b_scene.update()
        #b_scene.getCurrentCamera()
        
    except NIFImportError, e: # in that case, we raise a menu instead of an exception
        Blender.Window.DrawProgressBar(1.0, "Import Failed")
        print 'NIFImportError: ' + e.value
        Blender.Draw.PupMenu('ERROR%t|' + e.value)
        return

    Blender.Window.DrawProgressBar(1.0, "Finished")
    
# Reads the content of the current NIF tree branch to Blender recursively
def read_branch(niBlock):
    global b_scene
    # used to control the progress bar
    global block_count, blocks_read, read_progress
    blocks_read += 1.0
    if (blocks_read/block_count) >= (read_progress + 0.1):
        read_progress = blocks_read/block_count
        Blender.Window.DrawProgressBar(read_progress, "Reading NIF file")
    if not niBlock.is_null():
        type=niBlock.GetBlockType()
        if type == "NiNode" or type == "RootCollisionNode":
            niChildren = niBlock["Children"].asLinkList()
            #if (niBlock["Flags"].asInt() & 8) == 0 :
                # the node is a mesh influence
                #if inode.GetParent().asLink() is None or inode.GetParent().asLink()["Flags"].asInt() != 0x0002:
                #    # armature. The parent (can only be a NiNode) either doesn't exist or isn't an influence
                #    msg("%s is an armature" % fb_name(niBlock))
                #    children_list = []
                #    for child in [child for child in niChildren if child["Flags"].asInt() != 0x0002]:
                #        b_child = read_branch(child)
                #        if b_child: children_list.append(b_child)
                #    b_obj = fb_armature(niBlock)
                #    b_obj.makeParent(children_list)
                #    return b_obj
                #else:
                #    # bone. Do nothing, will be filled in by the armature
                #    return None
            #else:
                # grouping node
            b_obj = fb_empty(niBlock)
            b_children_list = []
            for child in niChildren:
                b_child_obj = read_branch(child)
                if b_child_obj: b_children_list.append(b_child_obj)
            b_obj.makeParent(b_children_list)
            b_obj.setMatrix(fb_matrix(niBlock))
            return b_obj
        elif type == "NiTriShape":
            return fb_mesh(niBlock)
        elif type == "NiTriStrips":
            return fb_mesh(niBlock)
        else:
            return None

#
# Get unique name for an object, preserving existing names
#
def fb_name(niBlock):
    uniqueInt = 0
    niName = niBlock["Name"].asString()
    name = niName
    try:
        while Blender.Object.Get(name):
            name = '%s.%02d' % (niName, uniqueInt)
            uniqueInt +=1
    except:
        pass
    return name

# Retrieves a niBlock's transform matrix as a Mathutil.Matrix
def fb_matrix(niBlock):
    inode=QueryNode(niBlock)
    m=inode.GetLocalBindPos()
    b_matrix = Matrix([m[0][0],m[0][1],m[0][2],m[0][3]],
                        [m[1][0],m[1][1],m[1][2],m[1][3]],
                        [m[2][0],m[2][1],m[2][2],m[2][3]],
                        [m[3][0],m[3][1],m[3][2],m[3][3]])
    return b_matrix

# Returns the scale correction matrix. A bit silly to calculate it all the time,
# but the overhead is minimal and when the GUI will work again this will be useful
def fb_scale_mat():
    s = 1.0/SCALE_CORRECTION 
    return Matrix([s,0,0,0],[0,s,0,0],[0,0,s,0],[0,0,0,1])

# Creates and returns a grouping empty
def fb_empty(niBlock):
    global b_scene
    b_empty = Blender.Object.New("Empty", fb_name(niBlock))
    b_scene.link(b_empty)
    return b_empty

# scans an armature hierarchy, and returns a whole armature.
# This is done outside the normal node tree scan to allow for positioning of the bones
def fb_armature(niBlock):
    #not yet implemented, for the moment I'll return a placeholder empty
    return fb_empty(niBlock)


def fb_texture( niSourceTexture ):
    if textures.has_key( niSourceTexture ):
        return textures[ niSourceTexture ]

    b_image = None
    
    niTexSource = niSourceTexture["Texture Source"].asTexSource()
    
    if niTexSource.useExternal:
        # the texture uses an external image file
        fn = niTexSource.fileName
        if fn[-4:] == ".dds":
            fn = fn[:-4] + ".tga"
        # go searching for it
        textureFile = None
        for texdir in TEXTURES_DIR.split(";") + [NIF_DIR, TEX_DIR]:
            if texdir == None: continue
            texdir.replace( '\\', Blender.sys.sep )
            texdir.replace( '/', Blender.sys.sep )
             # now a little trick, to satisfy many Morrowind mods
            if (fn[:9].lower() == 'textures\\') and (texdir[-9:].lower() == '\\textures'):
                tex = Blender.sys.join( texdir, fn[9:] ) # strip one of the two 'textures' from the path
            else:
                tex = Blender.sys.join( texdir, fn )
            print tex
            if (not re_dds.match(tex[-4:])) and Blender.sys.exists(tex) == 1: # Blender does not support .DDS
                textureFile = tex
                msg("Found %s" % textureFile, 3)
            else:
                # try other formats
                base=tex[:-4]
                for ext in ('.PNG','.png','.TGA','.tga','.BMP','.bmp','.JPG','.jpg'): # Blender does not support .DDS
                    print base+ext
                    if Blender.sys.exists(base+ext) == 1:
                        textureFile = base+ext
                        msg( "Found %s" % textureFile, 3 )
                        break
            if textureFile:
                b_image = Blender.Image.Load( textureFile )
                break
        else:
            print "texture %s not found"%niTexSource.fileName
    else:
        # the texture image is packed inside the nif -> extract it
        niPixelData = niSourceTexture["Texture Source"].asLink()
        iPixelData = QueryPixelData( niPixelData )
        
        width = iPixelData.GetWidth()
        height = iPixelData.GetHeight()
        
        if iPixelData.GetPixelFormat() == PX_FMT_RGB8:
            bpp = 24
        elif iPixelData.GetPixelFormat() == PX_FMT_RGBA8:
            bpp = 32
        else:
            bpp = None
        
        if bpp != None:
            b_image = Blender.Image.New( "TexImg", width, height, bpp )
            
            pixels = iPixelData.GetColors()
            for x in range( width ):
                Blender.Window.DrawProgressBar( float( x + 1 ) / float( width ), "Image Extraction")
                for y in range( height ):
                    pix = pixels[y*height+x]
                    b_image.setPixelF( x, (height-1)-y, ( pix.r, pix.g, pix.b, pix.a ) )
    
    if b_image != None:
        # create a texture using the loaded image
        b_texture = Blender.Texture.New()
        b_texture.setType( 'Image' )
        b_texture.setImage( b_image )
        b_texture.imageFlags = Blender.Texture.ImageFlags.INTERPOL + Blender.Texture.ImageFlags.MIPMAP
        return b_texture
    else:
        return None



def getTexturingPropertyCRC(textProperty):
    s = ''
    try:
        s = s + textProperty["Base Texture"].asString()
        s = s + textProperty["Glow Texture"].asString()
    except:
        pass
    id = int( 0 )
    for x in range( 0, len( s ), 2 ):
        try:
            id += ord( s[x+1] ) * 256
        except:
            pass
        id += ord( s[x] )
        if id > 0xffff:
            id = id - 0x10000 + 1
    return "%04X"%id


# Creates and returns a material
def fb_material(matProperty, textProperty):
    #First I check if the material already exists
    #The same material could be used with different textures
    # Note: this is a very buggy detection method:
    # what if another mesh uses a different material with the same name,
    # and with other material properties (such as NiAlphaProperty,
    # NiSpecularProperty...) involved?
    # Find better solution!!
    #name = matProperty["Name"].asString()
    #if textProperty.is_null() == False:
    #    name = "%s.%s" % (name, getTexturingPropertyCRC(textProperty))
    #try:
    #    material = Blender.Material.Get(name)
    #    msg("reusing material: %s " % name, 3)
    #    return material
    #except:
    #    msg('creating material: %s' % name, 2)
    #    material = Blender.Material.New(name)
    name = fb_name(matProperty)
    material = Blender.Material.New(name)
    # Sets the material colors
    # Specular color
    spec = matProperty["Specular Color"].asFloat3()
    material.setSpecCol([spec[0],spec[1],spec[2]])
    material.setSpec(1.0) # Blender multiplies specular color with this value
    # Diffuse color
    diff = matProperty["Diffuse Color"].asFloat3()
    material.setRGBCol([diff[0],diff[1],diff[2]])
    # Ambient & emissive color
    # We assume that ambient & emissive are fractions of the diffuse color.
    # If it is not an exact fraction, we average out.
    amb = matProperty["Ambient Color"].asFloat3()
    emit = matProperty["Emissive Color"].asFloat3()
    b_amb = 0.0
    b_emit = 0.0
    b_n = 0
    if (diff[0] > EPSILON):
        b_amb += amb[0]/diff[0]
        b_emit += emit[0]/diff[0]
        b_n += 1
    if (diff[1] > EPSILON):
        b_amb += amb[1]/diff[1]
        b_emit += emit[1]/diff[1]
        b_n += 1
    if (diff[2] > EPSILON):
        b_amb += amb[2]/diff[2]
        b_emit += emit[2]/diff[2]
        b_n += 1
    if (b_n > 0):
        b_amb /= b_n
        b_emit /= b_n
    if (b_amb > 1.0): b_amb = 1.0
    if (b_emit > 1.0): b_emit = 1.0
    material.setAmb(b_amb)
    material.setEmit(b_emit)
    # glossiness
    glossiness = matProperty["Glossiness"].asFloat()
    hardness = int(glossiness * 4) # just guessing really
    if hardness < 1: hardness = 1
    if hardness > 511: hardness = 511
    material.setHardness(hardness)
    # Alpha
    alpha = matProperty["Alpha"].asFloat()
    material.setAlpha(alpha)
    textures = []
    if textProperty.is_null() == False:
        BaseTextureSource = textProperty["Base Texture"].asTexDesc()
        if BaseTextureSource.isUsed:
            baseTexture = fb_texture(textProperty["Base Texture"].asLink())
            if baseTexture:
                # Sets the texture to use face UV coordinates.
                texco = Blender.Texture.TexCo.UV
                # Maps the texture to the base color channel. Not necessarily true.
                mapto = Blender.Texture.MapTo.COL
                # Sets the texture for the material
                material.setTexture(0, baseTexture, texco, mapto)
        GlowTextureSource = textProperty["Glow Texture"].asTexDesc()
        if GlowTextureSource.isUsed:
            glowTexture = fb_texture(textProperty["Glow Texture"].asLink())
            if glowTexture:
                # glow maps use alpha from rgb intensity
                glowTexture.imageFlags = glowTexture.imageFlags + Blender.Texture.ImageFlags.CALCALPHA
                # Sets the texture to use face UV coordinates.
                texco = Blender.Texture.TexCo.UV
                # Maps the texture to the base color channel. Not necessarily true.
                mapto = Blender.Texture.MapTo.COL | Texture.MapTo.EMIT
                # Sets the texture for the material
                material.setTexture(1, glowTexture, texco, mapto)
    return material



# Creates and returns a mesh
def fb_mesh(niBlock):
    global b_scene
    # Mesh name -> must be unique, so tag it if needed
    b_name=fb_name(niBlock)
    # No getRaw, this time we work directly on Blender's objects
    b_meshData = Blender.Mesh.New(b_name)
    b_mesh = Blender.Object.New("Mesh", b_name)
    # Mesh transform matrix, sets the transform matrix for the object.
    b_mesh.setMatrix(fb_matrix(niBlock))
    # Mesh geometry data. From this I can retrieve all geometry info
    data_blk = niBlock["Data"].asLink();
    iShapeData = QueryShapeData(data_blk)
    iTriShapeData = QueryTriShapeData(data_blk)
    iTriStripsData = QueryTriStripsData(data_blk)
    #vertices
    if not iShapeData:
        raise NIFImportError("no iShapeData returned. Node name: %s " % b_name)
    verts = iShapeData.GetVertices()
    # Faces
    if iTriShapeData:
        faces = iTriShapeData.GetTriangles()
    elif iTriStripsData:
        faces = iTriStripsData.GetTriangles()
    else:
        raise NIFImportError("no iTri*Data returned. Node name: %s " % b_name)
    # "Sticky" UV coordinates. these are transformed in Blender UV's
    # only the first UV set is loaded right now
    uvco = None
    if iShapeData.GetUVSetCount()>0:
        uvco = iShapeData.GetUVSet(0)
    # Vertex colors
    vcols = iShapeData.GetColors()
    # Vertex normals
    norms = iShapeData.GetNormals()

    # Construct vertex map to get unique vertex / normal pair list.
    # We use a Python dictionary to remove doubles and to keep track of indices.
    # While we are at it, we also add vertices while constructing the map.
    # Normals are calculated by Blender.
    n_map = {}
    v_map = [0]*len(verts) # pre-allocate memory, for faster performance
    b_v_index = 0
    for i, v in enumerate(verts):
        # The key k identifies unique vertex /normal pairs.
        # We use a tuple of ints for key, this works MUCH faster than a
        # tuple of floats.
        if norms:
            n = norms[i]
            k = (int(v.x*200),int(v.y*200),int(v.z*200),\
                 int(n.x*200),int(n.y*200),int(n.z*200))
        else:
            k = (int(v.x*200),int(v.y*200),int(v.z*200))
        # see if we already added this guy, and if so, what index
        try:
            n_map_k = n_map[k] # this is the bottle neck... can we speed this up?
        except KeyError:
            n_map_k = None
        if n_map_k == None:
            # not added: new vertex / normal pair
            n_map[k] = i         # unique vertex / normal pair with key k was added, with NIF index i
            v_map[i] = b_v_index # NIF vertex i maps to blender vertex b_v_index
            b_meshData.verts.extend(v.x, v.y, v.z) # add the vertex
            b_v_index += 1
        else:
            # already added
            v_map[i] = v_map[n_map_k] # NIF vertex i maps to Blender v_map[vertex n_map_nk]
    # release memory
    n_map = None

    # Adds the faces to the mesh
    f_map = [None]*len(faces)
    b_f_index = 0
    for i, f in enumerate(faces):
        if f.v1 != f.v2 and f.v1 != f.v3 and f.v2 != f.v3:
            v1=b_meshData.verts[v_map[f.v1]]
            v2=b_meshData.verts[v_map[f.v2]]
            v3=b_meshData.verts[v_map[f.v3]]
            tmp1 = len(b_meshData.faces)
            # extend checks for duplicate faces
            # see http://www.blender3d.org/documentation/240PythonDoc/Mesh.MFaceSeq-class.html
            b_meshData.faces.extend(v1, v2, v3)
            if tmp1 == len(b_meshData.faces): continue # duplicate face!
            f_map[i] = b_f_index # keep track of added faces, mapping NIF face index to Blender face index
            b_f_index += 1
    # at this point, deleted faces (redundant or duplicate)
    # satisfy f_map[i] = None
    
    # Sets face smoothing and material
    if norms:
        for f in b_meshData.faces:
            f.smooth = 1
            f.mat = 0
    else:
        for f in b_meshData.faces:
            f.smooth = 0 # no normals, turn off smoothing
            f.mat = 0

    # vertex colors
    vcol = iShapeData.GetColors()
    if len( vcol ) == 0:
        vcol = None
    else:
        b_meshData.vertexColors = 1
        for i, f in enumerate(faces):
            if f_map[i] == None: continue
            b_face = b_meshData.faces[f_map[i]]
            
            vc = vcol[f.v1]
            b_face.col[0].r = int(vc.r * 255)
            b_face.col[0].g = int(vc.g * 255)
            b_face.col[0].b = int(vc.b * 255)
            b_face.col[0].a = int(vc.a * 255)
            vc = vcol[f.v2]
            b_face.col[1].r = int(vc.r * 255)
            b_face.col[1].g = int(vc.g * 255)
            b_face.col[1].b = int(vc.b * 255)
            b_face.col[1].a = int(vc.a * 255)
            vc = vcol[f.v3]
            b_face.col[2].r = int(vc.r * 255)
            b_face.col[2].g = int(vc.g * 255)
            b_face.col[2].b = int(vc.b * 255)
            b_face.col[2].a = int(vc.a * 255)
        # vertex colors influence lighting...
        # so now we have to set the VCOL_LIGHT flag on the material
        # see below
    # UV coordinates
    # Nif files only support 'sticky' UV coordinates, and duplicates vertices to emulate hard edges and UV seams.
    # Essentially whenever an hard edge or an UV seam is present the mesh this is converted to an open mesh.
    # Blender also supports 'per face' UV coordinates, this could be a problem when exporting.
    # Also, NIF files support a series of texture sets, each one with its set of texture coordinates. For example
    # on a single "material" I could have a base texture, with a decal texture over it mapped on another set of UV
    # coordinates. I don't know if Blender can do the same.

    if uvco:
        # Sets the face UV's for the mesh on. The NIF format only supports vertex UV's,
        # but Blender only allows explicit editing of face UV's, so I'll load vertex UV's like face UV's
        b_meshData.faceUV = 1
        b_meshData.vertexUV = 0
        for i, f in enumerate(faces):
            if f_map[i] == None: continue
            uvlist = []
            for v in (f.v1, f.v2, f.v3):
                uv=uvco[v]
                uvlist.append(Vector(uv.u, 1.0 - uv.v))
            b_meshData.faces[f_map[i]].uv = tuple(uvlist)
    
    # Texturing property. From this I can retrieve texture info
    textProperty = niBlock["Properties"].FindLink( "NiTexturingProperty" )
    matProperty = niBlock["Properties"].FindLink("NiMaterialProperty" )
    # Sets the material for this mesh. NIF files only support one material for each mesh
    if matProperty.is_null() == False:
        material = fb_material(matProperty, textProperty)
        alphaProperty = niBlock["Properties"].FindLink("NiAlphaProperty")
        specProperty = niBlock["Properties"].FindLink("NiSpecularProperty")
        # Texture. First one is the base texture.
        # Let's just focus on the base texture for transparency, etc.
        mtex = material.getTextures()[0]
        # if the mesh has an alpha channel
        if alphaProperty.is_null() == False:
            material.mode |= Blender.Material.Modes.ZTRANSP # enable z-buffered transparency
            # if the image has an alpha channel => then this overrides the material alpha value
            if mtex:
                if mtex.tex.image.depth == 32: # ... crappy way to check for alpha channel in texture
                    mtex.tex.imageFlags |= Blender.Texture.ImageFlags.USEALPHA # use the alpha channel
                    mtex.mapto |=  Blender.Texture.MapTo.ALPHA # and map the alpha channel to transparency
                    material.setAlpha(0.0) # for proper display in Blender, we must set the alpha value to 0 and the "Val" slider in the texture Map To tab to the NIF material alpha value (but we do not have access to that button yet... we have to wait until it gets supported by the Blender Python API...)
        else:
            # no alpha property: force alpha 1.0 in Blender
            material.setAlpha(1.0)
        if specProperty.is_null() == True:
            # no specular property: specular color is ignored
            # which means that the specular color should be black
            # and glossiness (specularity) should be zero
            material.setSpecCol([0.0, 0.0, 0.0])
            material.setSpec(0.0)
        if b_meshData.vertexColors == 1:
            if mtex:
                material.mode |= Blender.Material.Modes.VCOL_LIGHT # textured material: vertex colors influence lighting
            else:
                material.mode |= Blender.Material.Modes.VCOL_PAINT # non-textured material: vertex colors incluence color
        b_meshData.materials = [material]
        #If there's a base texture assigned to this material sets it to be displayed in Blender's 3D view
        if mtex:
            imgobj = mtex.tex.getImage()
            if imgobj:
                for f in b_meshData.faces:
                    f.image = imgobj # does not seem to work anymore???

    b_mesh.link(b_meshData)
    b_scene.link(b_mesh)

    # Skinning info, for meshes affected by bones. Adding groups to a mesh can be done only after this is already
    # linked to an object.
    skinInstance = niBlock["Skin Instance"].asLink()
    if skinInstance.is_null() == False:
        skinData = skinInstance["Data"].asLink()
        iSkinData = QuerySkinData(skinData)
        bones = iSkinData.GetBones()
        for idx, bone in enumerate(bones):
            weights = iSkinData.GetWeights(bone)
            groupName = bone["Name"].asString()
            b_meshData.addVertGroup(groupName)
            for vert, weight in weights.iteritems():
                b_meshData.assignVertsToGroup(groupName, [v_map[vert]], weight, Blender.Mesh.AssignModes.REPLACE)

    b_meshData.calcNormals() # let Blender calculate vertex normals
    """
    # morphing
    #morphCtrl = triShape.getNiGeomMorpherController()
    if morphCtrl:
        morphData = morphCtrl.getNiMorphData()
        if morphData and ( morphData.NumMorphBlocks > 0 ):
            # insert base key
            meshData.insertKey( 0, 'relative' )
            frameCnt, frameType, frames, baseverts = morphData.MorphBlocks[0]
            ipo = Blender.Ipo.New( 'Key', 'KeyIpo' )
            # iterate through the list of other morph keys
            for key in range( 1, morphData.NumMorphBlocks ):
                frameCnt, frameType, frames, verts = morphData.MorphBlocks[key]
                # for each vertex calculate the key position from base pos + delta offset
                for count in range( morphData.NumVertices ):
                    x, y, z = baseverts[count]
                    dx, dy, dz = verts[count]
                    meshData.verts[vertmap[count]].co[0] = x + dx
                    meshData.verts[vertmap[count]].co[1] = y + dy
                    meshData.verts[vertmap[count]].co[2] = z + dz
                # update the mesh and insert key
                meshData.calcNormals() # recalculate normals
                meshData.insertKey(key, 'relative')
                # set up the ipo key curve
                curve = ipo.addCurve( 'Key %i'%key )
                # dunno how to set up the bezier triples -> switching to linear instead
                curve.setInterpolation( 'Linear' )
                # select extrapolation
                if ( morphCtrl.Flags == 0x000c ):
                    curve.setExtrapolation( 'Constant' )
                elif ( morphCtrl.Flags == 0x0008 ):
                    curve.setExtrapolation( 'Cyclic' )
                else:
                    msg( 'dunno which extrapolation to use: using constant instead', 2 )
                    curve.setExtrapolation( 'Constant' )
                # set up the curve's control points
                for count in range( frameCnt ):
                    time, x, y, z = frames[count]
                    frame = time * Blender.Scene.getCurrent().getRenderingContext().framesPerSec() + 1
                    curve.addBezier( ( frame, x ) )
                # finally: return to base position
                for count in range( morphData.NumVertices ):
                    x, y, z = baseverts[count]
                    meshData.verts[vertmap[count]].co[0] = x
                    meshData.verts[vertmap[count]].co[1] = y
                    meshData.verts[vertmap[count]].co[2] = z
                meshData.update(1) # recalculate normals
            # assign ipo to mesh (not supported by Blender API?)
            #meshData.setIpo( ipo )
    """
    return b_mesh




# calculate distance between two Float3 vectors
def get_distance(v, w):
    return ((v[0]-w[0])*(v[0]-w[0]) + (v[1]-w[1])*(v[1]-w[1]) + (v[2]-w[2])*(v[2]-w[2])) ** 0.5


#----------------------------------------------------------------------------------------------------#
#----------------------------------------------------------------------------------------------------#
#-------- Run importer GUI.
#----------------------------------------------------------------------------------------------------#
#----------------------------------------------------------------------------------------------------#
def gui_draw():
    global gui_texpath, gui_scale, gui_last
    global SCALE_CORRECTION, FORCE_DDS, STRIP_TEXPATH, SEAMS_IMPORT, LAST_IMPORTED, TEXTURES_DIR
    
    BGL.glClearColor(0.753, 0.753, 0.753, 0.0)
    BGL.glClear(BGL.GL_COLOR_BUFFER_BIT)

    BGL.glColor3f(0.000, 0.000, 0.000)
    BGL.glRasterPos2i(8, 92)
    Draw.Text('Tex Path:')
    BGL.glRasterPos2i(8, 188)
    Draw.Text('Seams:')

    Draw.Button('Browse', 1, 8, 48, 55, 23, '')
    Draw.Button('Import NIF', 2, 8, 8, 87, 23, '')
    Draw.Button('Cancel', 3, 208, 8, 71, 23, '')
    Draw.Toggle('Smoothing Flag (Slow)', 6, 88, 112, 191, 23, SEAMS_IMPORT == 2, 'Import seams and convert them to "the Blender way", is slow and imperfect, unless model was created by Blender and had no duplicate vertices.')
    Draw.Toggle('Vertex Duplication (Slow)', 7, 88, 144, 191, 23, SEAMS_IMPORT == 1, 'Perfect but slow, this is the preferred method if the model you are importing is not too large.')
    Draw.Toggle('Vertex Duplication (Fast)', 8, 88, 176, 191, 23, SEAMS_IMPORT == 0, 'Fast but imperfect: may introduce unwanted cracks in UV seams')
    gui_texpath = Draw.String('', 4, 72, 80, 207, 23, TEXTURES_DIR, 512, 'Semi-colon separated list of texture directories.')
    gui_last = Draw.String('', 5, 72, 48, 207, 23, LAST_IMPORTED, 512, '')
    gui_scale = Draw.Slider('Scale Correction: ', 9, 8, 208, 271, 23, SCALE_CORRECTION, 0.01, 100, 0, 'How many NIF units is one Blender unit?')

def gui_select(filename):
    global LAST_IMPORTED
    LAST_IMPORTED = filename
    Draw.Redraw(1)
    
def gui_evt_key(evt, val):
    if (evt == Draw.QKEY and not val):
        Draw.Exit()

def gui_evt_button(evt):
    global gui_texpath, gui_scale, gui_last
    global SCALE_CORRECTION, force_dds, strip_texpath, SEAMS_IMPORT, LAST_IMPORTED, TEXTURES_DIR
    
    if evt == 6: #Toggle3
        SEAMS_IMPORT = 2
        Draw.Redraw(1)
    elif evt == 7: #Toggle2
        SEAMS_IMPORT = 1
        Draw.Redraw(1)
    elif evt == 8: #Toggle1
        SEAMS_IMPORT = 0
        Draw.Redraw(1)
    elif evt == 1: # Browse
        Blender.Window.FileSelector(gui_select, 'Select')
        Draw.Redraw(1)
    elif evt == 4: # TexPath
        TEXTURES_DIR = gui_texpath.val
    elif evt == 5: # filename
        LAST_IMPORTED = gui_last.val
    elif evt == 9: # scale
        SCALE_CORRECTION = gui_scale.val
    elif evt == 2: # Import NIF
        # Stop GUI.
        gui_last = None
        gui_texpath = None
        gui_scale = None
        Draw.Exit()
        gui_import()
    elif evt == 3: # Cancel
        gui_last = None
        gui_texpath = None
        gui_scale = None
        Draw.Exit()

def gui_import():
    # Save options for next time.
    update_registry()
    # Import file.
    if SEAMS_IMPORT == 2:
        msg("Smoothing import not implemented yet, selecting slow vertex duplication method instead.", 1)
        SEAMS_IMPORT = 1
    import_nif(LAST_IMPORTED)

if USE_GUI:
    Draw.Register(gui_draw, gui_evt_key, gui_evt_button)
else:
    if IMPORT_DIR:
        Blender.Window.FileSelector(import_nif, 'Import NIF', IMPORT_DIR)
    else:
        Blender.Window.FileSelector(import_nif, 'Import NIF')