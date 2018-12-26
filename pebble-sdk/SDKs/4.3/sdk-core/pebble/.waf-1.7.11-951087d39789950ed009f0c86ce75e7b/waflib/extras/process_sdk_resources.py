#! /usr/bin/env python
# encoding: utf-8
# WARNING! Do not edit! http://waf.googlecode.com/git/docs/wafbook/single.html#_obtaining_the_waf_file

import copy
from waflib import Node
from resources.find_resource_filename import find_most_specific_filename
from resources.types.resource_definition import ResourceDefinition
from resources.types.resource_object import ResourceObject
from resources.resource_map import resource_generator
import resources.resource_map.resource_generator_bitmap
import resources.resource_map.resource_generator_font
import resources.resource_map.resource_generator_js
import resources.resource_map.resource_generator_pbi
import resources.resource_map.resource_generator_png
import resources.resource_map.resource_generator_raw
from sdk_helpers import is_sdk_2x,validate_resource_not_larger_than
def _preprocess_resource_ids(bld,resources_list,has_published_media=False):
	resource_id_mapping={}
	next_id=1
	if has_published_media:
		resource_id_mapping['TIMELINE_LUT']=next_id
		next_id+=1
	for res_id,res in enumerate(resources_list,start=next_id):
		if isinstance(res,Node.Node):
			if res.name=='timeline_resource_table.reso':
				continue
			res_name=ResourceObject.load(res.abspath()).definition.name
			resource_id_mapping[res_name]=res_id
		else:
			resource_id_mapping[res.name]=res_id
	bld.env.RESOURCE_ID_MAPPING=resource_id_mapping
def generate_resources(bld,resource_source_path):
	resources_json=getattr(bld.env,'RESOURCES_JSON',[])
	published_media_json=getattr(bld.env,'PUBLISHED_MEDIA_JSON',[])
	if resource_source_path:
		resources_node=bld.path.find_node(resource_source_path)
	else:
		resources_node=bld.path.find_node('resources')
	resource_file_mapping={}
	for resource in resources_json:
		resource_file_mapping[resource['name']]=(find_most_specific_filename(bld,bld.env,resources_node,resource['file']))
	bld.load('generate_pbpack generate_resource_ball generate_resource_id_header')
	bld.load('process_timeline_resources')
	resource_definitions=[]
	max_menu_icon_dimensions=(25,25)
	for r in resources_json:
		if'menuIcon'in r and r['menuIcon']:
			res_file=(resources_node.find_node(find_most_specific_filename(bld,bld.env,resources_node,str(r['file'])))).abspath()
			if not validate_resource_not_larger_than(bld,res_file,dimensions=max_menu_icon_dimensions):
				bld.fatal("menuIcon resource '{}' exceeds the maximum allowed dimensions of {}".format(r['name'],max_menu_icon_dimensions))
		defs=resource_generator.definitions_from_dict(bld,r,resource_source_path)
		for d in defs:
			if not d.is_in_target_platform(bld):
				continue
			if d.type=='png-trans':
				for suffix in('WHITE','BLACK'):
					new_definition=copy.deepcopy(d)
					new_definition.name='%s_%s'%(d.name,suffix)
					resource_definitions.append(new_definition)
				continue
			if d.type=='png'and is_sdk_2x(bld.env.SDK_VERSION_MAJOR,bld.env.SDK_VERSION_MINOR):
				d.type='pbi'
			resource_definitions.append(d)
	bld_dir=bld.path.get_bld().make_node(bld.env.BUILD_DIR)
	lib_resources=[]
	for lib in bld.env.LIB_JSON:
		if'pebble'not in lib or'resources'not in lib['pebble']:
			continue
		if'media'not in lib['pebble']['resources']or not lib['pebble']['resources']['media']:
			continue
		lib_path=bld.path.find_node(lib['path'])
		try:
			resources_path=lib_path.find_node('resources').find_node(bld.env.PLATFORM_NAME)
		except AttributeError:
			bld.fatal("Library {} is missing resources".format(lib['name']))
		else:
			if resources_path is None:
				bld.fatal("Library {} is missing resources for the {} platform".format(lib['name'],bld.env.PLATFORM_NAME))
		for lib_resource in bld.env.LIB_RESOURCES_JSON.get(lib['name'],[]):
			if'targetPlatforms'in lib_resource:
				if bld.env.PLATFORM_NAME not in lib_resource['targetPlatforms']:
					continue
			reso_file='{}.{}.reso'.format(lib_resource['file'],lib_resource['name'])
			resource_node=resources_path.find_node(reso_file)
			if resource_node is None:
				bld.fatal("Library {} is missing the {} resource for the {} platform".format(lib['name'],lib_resource['name'],bld.env.PLATFORM_NAME))
			if lib_resource['name']in resource_file_mapping:
				bld.fatal("Duplicate resource IDs are not permitted. Package resource {} uses the ""same resource ID as another resource already in this project.".format(lib_resource['name']))
			resource_file_mapping[lib_resource['name']]=resource_node
			lib_resources.append(resource_node)
	resources_list=[]
	if resource_definitions:
		resources_list.extend(resource_definitions)
	if lib_resources:
		resources_list.extend(lib_resources)
	build_type=getattr(bld.env,'BUILD_TYPE','app')
	resource_ball=bld_dir.make_node('system_resources.resball')
	project_resource_ball=None
	if build_type=='lib':
		project_resource_ball=bld_dir.make_node('project_resources.resball')
		bld.env.PROJECT_RESBALL=project_resource_ball
	if published_media_json:
		if build_type!='lib':
			timeline_resource_table=bld_dir.make_node('timeline_resource_table.reso')
			resources_list.append(timeline_resource_table)
			_preprocess_resource_ids(bld,resources_list,True)
			bld(features='process_timeline_resources',published_media=published_media_json,timeline_reso=timeline_resource_table,layouts_json=bld_dir.make_node('layouts.json'),resource_mapping=resource_file_mapping,vars=['RESOURCE_ID_MAPPING','PUBLISHED_MEDIA_JSON'])
	bld(features='generate_resource_ball',resources=resources_list,resource_ball=resource_ball,project_resource_ball=project_resource_ball,vars=['RESOURCES_JSON','LIB_RESOURCES_JSON','RESOURCE_ID_MAPPING'])
	resource_id_header=bld_dir.make_node('src/resource_ids.auto.h')
	bld.env.RESOURCE_ID_HEADER=resource_id_header.abspath()
	bld(features='generate_resource_id_header',resource_ball=resource_ball,resource_id_header_target=resource_id_header,use_extern=build_type=='lib',use_define=build_type=='app',published_media=published_media_json)
	resource_id_definitions=bld_dir.make_node('src/resource_ids.auto.c')
	bld.env.RESOURCE_ID_DEFINITIONS=resource_id_definitions.abspath()
	bld(features='generate_resource_id_definitions',resource_ball=resource_ball,resource_id_definitions_target=resource_id_definitions,published_media=published_media_json)
	if not bld.env.BUILD_TYPE or bld.env.BUILD_TYPE in('app','rocky'):
		pbpack=bld_dir.make_node('app_resources.pbpack')
		bld(features='generate_pbpack',resource_ball=resource_ball,pbpack_target=pbpack,is_system=False)
