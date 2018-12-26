#! /usr/bin/env python
# encoding: utf-8
# WARNING! Do not edit! http://waf.googlecode.com/git/docs/wafbook/single.html#_obtaining_the_waf_file

import json
import os
import struct
import re
from waflib import Logs
from pebble_package import LibraryPackage
from pebble_sdk_platform import pebble_platforms,maybe_import_internal
from pebble_sdk_version import set_env_sdk_version
from resources.types.resource_object import ResourceObject
def _get_pbi_size(data):
	width=struct.unpack('<h',data[8:10])[0]
	height=struct.unpack('<h',data[10:12])[0]
	return width,height
def _get_pdc_size(data):
	width=struct.unpack('>I',data[6:8])[0]
	height=struct.unpack('>I',data[8:10])[0]
	return width,height
def _get_png_size(data):
	assert data[:4]=='IHDR'
	width=struct.unpack('>I',data[4:8])[0]
	height=struct.unpack('>I',data[8:12])[0]
	return width,height
def _get_supported_platforms(ctx,has_rocky=False):
	sdk_check_nodes=['lib/libpebble.a','pebble_app.ld.template','tools','include','include/pebble.h']
	supported_platforms=os.listdir(ctx.env.PEBBLE_SDK_ROOT)
	invalid_platforms=[]
	for platform in supported_platforms:
		pebble_sdk_platform=ctx.root.find_node(ctx.env.PEBBLE_SDK_ROOT).find_node(platform)
		for node in sdk_check_nodes:
			if pebble_sdk_platform.find_node(node)is None:
				if ctx.root.find_node(ctx.env.PEBBLE_SDK_COMMON).find_node(node)is None:
					invalid_platforms.append(platform)
					break
	for platform in invalid_platforms:
		supported_platforms.remove(platform)
	if has_rocky and'aplite'in supported_platforms:
		supported_platforms.remove('aplite')
	ctx.env.SUPPORTED_PLATFORMS=supported_platforms
	return supported_platforms
def append_to_attr(self,attr,new_values):
	values=self.to_list(getattr(self,attr,[]))
	if not isinstance(new_values,list):
		new_values=[new_values]
	values.extend(new_values)
	setattr(self,attr,values)
def configure_libraries(ctx,libraries):
	dependencies=libraries.keys()
	lib_json=[]
	lib_resources_json={}
	index=0
	while index<len(dependencies):
		info,resources,additional_deps=process_package(ctx,dependencies[index])
		lib_json.append(info)
		lib_resources_json[dependencies[index]]=resources
		dependencies.extend(additional_deps)
		index+=1
	ctx.env.LIB_JSON=lib_json
	if lib_resources_json:
		ctx.env.LIB_RESOURCES_JSON=lib_resources_json
def configure_platform(ctx,platform):
	pebble_sdk_root=get_node_from_abspath(ctx,ctx.env.PEBBLE_SDK_ROOT)
	ctx.env.PLATFORM=pebble_platforms[platform]
	ctx.env.PEBBLE_SDK_PLATFORM=pebble_sdk_root.find_node(str(platform)).abspath()
	ctx.env.PLATFORM_NAME=ctx.env.PLATFORM['NAME']
	for attribute in['DEFINES']:
		ctx.env.append_unique(attribute,ctx.env.PLATFORM[attribute])
	for attribute in['BUILD_DIR','BUNDLE_BIN_DIR']:
		ctx.env[attribute]=ctx.env.PLATFORM[attribute]
	ctx.env.append_value('INCLUDES',ctx.env.BUILD_DIR)
	ctx.msg("Found Pebble SDK for {} in:".format(platform),ctx.env.PEBBLE_SDK_PLATFORM)
	process_info=(pebble_sdk_root.find_node(str(platform)).find_node('include/pebble_process_info.h'))
	set_env_sdk_version(ctx,process_info)
	if is_sdk_2x(ctx.env.SDK_VERSION_MAJOR,ctx.env.SDK_VERSION_MINOR):
		ctx.env.append_value('DEFINES',"PBL_SDK_2")
	else:
		ctx.env.append_value('DEFINES',"PBL_SDK_3")
	ctx.load('pebble_sdk_gcc')
def find_sdk_component(ctx,env,component):
	return(ctx.root.find_node(env.PEBBLE_SDK_PLATFORM).find_node(component)or ctx.root.find_node(env.PEBBLE_SDK_COMMON).find_node(component))
def get_node_from_abspath(ctx,path):
	return ctx.root.make_node(path)
def get_target_platforms(ctx):
	supported_platforms=_get_supported_platforms(ctx,ctx.env.BUILD_TYPE=='rocky')
	if not ctx.env.REQUESTED_PLATFORMS:
		target_platforms=supported_platforms
	else:
		target_platforms=list(set(supported_platforms)&set(ctx.env.REQUESTED_PLATFORMS))
	if not target_platforms:
		ctx.fatal("No valid targetPlatforms specified in appinfo.json. Valid options are {}".format(supported_platforms))
	ctx.env.TARGET_PLATFORMS=sorted([p.encode('utf-8')for p in target_platforms],reverse=True)
	return target_platforms
def is_sdk_2x(major,minor):
	LAST_2X_MAJOR_VERSION=5
	LAST_2X_MINOR_VERSION=19
	return(major,minor)<=(LAST_2X_MAJOR_VERSION,LAST_2X_MINOR_VERSION)
def process_package(ctx,package,root_lib_node=None):
	resources_json={}
	if not root_lib_node:
		root_lib_node=ctx.path.find_node(ctx.env.LIB_DIR)
		if root_lib_node is None:
			ctx.fatal("Missing {} directory".format(ctx.env.LIB_DIR))
	lib_node=root_lib_node.find_node(str(package))
	if lib_node is None:
		ctx.fatal("Missing library for {} in {}".format(str(package),ctx.env.LIB_DIR))
	else:
		libinfo_node=lib_node.find_node('package.json')
		if libinfo_node is None:
			ctx.fatal("Missing package.json for {} library".format(str(package)))
		else:
			if lib_node.find_node(ctx.env.LIB_DIR):
				error_str=("ERROR: Multiple versions of the same package are not supported by ""the Pebble SDK due to namespace issues during linking. Package '{}' ""contains the following duplicate and incompatible dependencies, ""which may lead to additional build errors and/or unpredictable ""runtime behavior:\n".format(package))
				packages_str=""
				for package in lib_node.find_node(ctx.env.LIB_DIR).ant_glob('**/package.json'):
					with open(package.abspath())as f:
						info=json.load(f)
					if not dict(ctx.env.PROJECT_INFO).get('enableMultiJS',False):
						if not'pebble'in info:
							continue
					packages_str+="      '{}': '{}'\n".format(info['name'],info['version'])
				if packages_str:
					Logs.pprint("RED",error_str+packages_str)
			with open(libinfo_node.abspath())as f:
				libinfo=json.load(f)
			if'pebble'in libinfo:
				if ctx.env.BUILD_TYPE=='rocky':
					ctx.fatal("Packages containing C binaries are not compatible with Rocky.js ""projects. Please remove '{}' from the `dependencies` object in ""package.json".format(libinfo['name']))
				libinfo['path']=lib_node.make_node('dist').path_from(ctx.path)
				if'resources'in libinfo['pebble']:
					if'media'in libinfo['pebble']['resources']:
						resources_json=libinfo['pebble']['resources']['media']
				dist_node=lib_node.find_node('dist.zip')
				if not dist_node:
					ctx.fatal("Missing dist.zip file for {}. Are you sure this is a Pebble ""library?".format(package))
				lib_package=LibraryPackage(dist_node.abspath())
				lib_package.unpack(libinfo['path'])
				lib_js_node=lib_node.find_node('dist/js')
				if lib_js_node:
					libinfo['js_paths']=[lib_js.path_from(ctx.path)for lib_js in lib_js_node.ant_glob(['**/*.js','**/*.json'])]
			else:
				libinfo['js_paths']=[lib_js.path_from(ctx.path)for lib_js in lib_node.ant_glob(['**/*.js','**/*.json'],excl="**/*.min.js")]
			dependencies=libinfo['dependencies'].keys()if'dependencies'in libinfo else[]
			return libinfo,resources_json,dependencies
def truncate_to_32_bytes(name):
	return name[:30]+'..'if len(name)>32 else name
def validate_message_keys_object(ctx,project_info,info_json_type):
	if'appKeys'in project_info and info_json_type=='package.json':
		ctx.fatal("Project contains an invalid object `appKeys` in package.json. Please use ""`messageKeys` instead.")
	if'messageKeys'in project_info and info_json_type=='appinfo.json':
		ctx.fatal("Project contains an invalid object `messageKeys` in appinfo.json. Please use ""`appKeys` instead.")
def validate_resource_not_larger_than(ctx,resource_file,dimensions=None,width=None,height=None):
	if not dimensions and not width and not height:
		raise TypeError("Missing values for maximum width and/or height to validate against")
	if dimensions:
		width,height=dimensions
	with open(resource_file,'rb')as f:
		if resource_file.endswith('.reso'):
			reso=ResourceObject.load(resource_file)
			if reso.definition.type=='bitmap':
				storage_format=reso.definition.storage_format
			else:
				storage_format=reso.definition.type
			if storage_format=='pbi':
				resource_size=_get_pbi_size(reso.data)
			elif storage_format=='png':
				resource_size=_get_png_size(reso.data[12:])
			elif storage_format=='raw':
				try:
					assert reso.data[4:]=='PDCI'
				except AssertionError:
					ctx.fatal("Unsupported published resource type for {}".format(resource_file))
				else:
					resource_size=_get_pdc_size(reso.data[4:])
		else:
			data=f.read(24)
			if data[1:4]=='PNG':
				resource_size=_get_png_size(data[12:])
			elif data[:4]=='PDCI':
				resource_size=_get_pdc_size(data[4:])
			else:
				ctx.fatal("Unsupported published resource type for {}".format(resource_file))
	if width and height:
		return resource_size<=(width,height)
	elif width:
		return resource_size[0]<=width
	elif height:
		return resource_size[1]<=height
def wrap_task_name_with_platform(self):
	src_str=' '.join([a.nice_path()for a in self.inputs])
	tgt_str=' '.join([a.nice_path()for a in self.outputs])
	sep=' -> 'if self.outputs else''
	name=self.__class__.__name__.replace('_task','')
	if self.env.PLATFORM_NAME:
		name=self.env.PLATFORM_NAME+" | "+name
	return'%s: %s%s%s\n'%(name,src_str,sep,tgt_str)
