#! /usr/bin/env python
# encoding: utf-8
# WARNING! Do not edit! http://waf.googlecode.com/git/docs/wafbook/single.html#_obtaining_the_waf_file

import json
import sdk_paths
from process_sdk_resources import generate_resources
from sdk_helpers import(configure_libraries,configure_platform,get_target_platforms,validate_message_keys_object)
def options(opt):
	opt.load('pebble_sdk_common')
	opt.add_option('-t','--timestamp',dest='timestamp',help="Use a specific timestamp to label this package (ie, your repository's last commit time), ""defaults to time of build")
def configure(conf):
	conf.load('pebble_sdk_common')
	if conf.options.timestamp:
		conf.env.TIMESTAMP=conf.options.timestamp
	conf.env.BUNDLE_NAME="dist.zip"
	package_json_node=conf.path.get_src().find_node('package.json')
	if package_json_node is None:
		conf.fatal('Could not find package.json')
	with open(package_json_node.abspath(),'r')as f:
		package_json=json.load(f)
	project_info=package_json['pebble']
	project_info['name']=package_json['name']
	validate_message_keys_object(conf,project_info,'package.json')
	conf.env.PROJECT_INFO=project_info
	conf.env.BUILD_TYPE='lib'
	conf.env.REQUESTED_PLATFORMS=project_info.get('targetPlatforms',[])
	conf.env.LIB_DIR="node_modules"
	get_target_platforms(conf)
	if'dependencies'in package_json:
		configure_libraries(conf,package_json['dependencies'])
	conf.load('process_message_keys')
	if'resources'in project_info and'media'in project_info['resources']:
		conf.env.RESOURCES_JSON=package_json['pebble']['resources']['media']
	base_env=conf.env
	for platform in conf.env.TARGET_PLATFORMS:
		conf.setenv(platform,base_env)
		configure_platform(conf,platform)
	conf.setenv('')
def build(bld):
	bld.load('pebble_sdk_common')
	cached_env=bld.env
	for platform in bld.env.TARGET_PLATFORMS:
		bld.env=bld.all_envs[platform]
		if bld.env.USE_GROUPS:
			bld.set_group(bld.env.PLATFORM_NAME)
		resource_path=None
		if bld.env.RESOURCES_JSON:
			try:
				resource_path=bld.path.find_node('src').find_node('resources').path_from(bld.path)
			except AttributeError:
				bld.fatal("Unable to locate resources at src/resources/")
		generate_resources(bld,resource_path)
	bld.env=cached_env
