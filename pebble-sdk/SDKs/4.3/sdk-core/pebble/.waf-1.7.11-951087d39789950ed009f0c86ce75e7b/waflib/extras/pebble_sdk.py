#! /usr/bin/env python
# encoding: utf-8
# WARNING! Do not edit! http://waf.googlecode.com/git/docs/wafbook/single.html#_obtaining_the_waf_file

import json
from waflib.Configure import conf
from waflib.Errors import ConfigurationError
from waflib import Logs
import sdk_paths
from generate_appinfo import generate_appinfo_c
from process_sdk_resources import generate_resources
import report_memory_usage
from sdk_helpers import(configure_libraries,configure_platform,find_sdk_component,get_target_platforms,truncate_to_32_bytes,validate_message_keys_object)
def _extract_project_info(conf,info_json,json_filename):
	if'pebble'in info_json:
		project_info=info_json['pebble']
		validate_message_keys_object(conf,project_info,'package.json')
		project_info['name']=info_json['name']
		project_info['shortName']=project_info['longName']=project_info['displayName']
		if not info_json['version']:
			conf.fatal("Project is missing a version")
		version=_validate_version(conf,info_json['version'])
		project_info['versionLabel']=version
		if isinstance(info_json['author'],basestring):
			project_info['companyName']=(info_json['author'].split('(',1)[0].split('<',1)[0].strip())
		elif isinstance(info_json['author'],dict)and'name'in info_json['author']:
			project_info['companyName']=info_json['author']['name']
		else:
			conf.fatal("Missing author name in project info")
	elif'package.json'==json_filename:
		try:
			with open(conf.path.get_src().find_node('appinfo.json').abspath(),'r')as f:
				info_json=json.load(f)
		except AttributeError:
			conf.fatal("Could not find Pebble project info in package.json and no appinfo.json file"" exists")
		project_info=info_json
		validate_message_keys_object(conf,project_info,'appinfo.json')
	else:
		project_info=info_json
		validate_message_keys_object(conf,project_info,'appinfo.json')
	return project_info
def _generate_appinfo_c_file(task):
	info_json=dict(getattr(task.generator.env,task.vars[0]))
	info_json['shortName']=truncate_to_32_bytes(info_json['shortName'])
	info_json['companyName']=truncate_to_32_bytes(info_json['companyName'])
	current_platform=task.generator.env.PLATFORM_NAME
	generate_appinfo_c(info_json,task.outputs[0].abspath(),current_platform)
def _write_appinfo_json_file(task):
	appinfo=dict(getattr(task.generator.env,task.vars[0]))
	capabilities=appinfo.get('capabilities',[])
	for lib in dict(task.generator.env).get('LIB_JSON',[]):
		if'pebble'in lib:
			capabilities.extend(lib['pebble'].get('capabilities',[]))
	appinfo['capabilities']=list(set(capabilities))
	for key in task.env.BLOCK_MESSAGE_KEYS:
		del appinfo['appKeys'][key]
	if appinfo:
		with open(task.outputs[0].abspath(),'w')as f:
			json.dump(appinfo,f,indent=4)
	else:
		task.generator.bld.fatal("Unable to find project info to populate appinfo.json file with")
def _validate_version(ctx,original_version):
	version=original_version.split('.')
	if len(version)>3:
		ctx.fatal("App versions must be of the format MAJOR or MAJOR.MINOR or MAJOR.MINOR.0. An ""invalid version of {} was specified for the app. Try {}.{}.0 instead".format(original_version,version[0],version[1]))
	elif not(0<=int(version[0])<=255):
		ctx.fatal("An invalid or out of range value of {} was specified for the major version of ""the app. The valid range is 0-255.".format(version[0]))
	elif not(0<=int(version[1])<=255):
		ctx.fatal("An invalid or out of range value of {} was specified for the minor version of ""the app. The valid range is 0-255.".format(version[1]))
	elif len(version)>2 and not(int(version[2])==0):
		ctx.fatal("The patch version of an app must be 0, but {} was specified ({}). Try {}.{}.0 ""instead.".format(version[2],original_version,version[0],version[1]))
	return version[0]+'.'+version[1]
def options(opt):
	opt.load('pebble_sdk_common')
	opt.add_option('-t','--timestamp',dest='timestamp',help="Use a specific timestamp to label this package (ie, your repository's ""last commit time), defaults to time of build")
def configure(conf):
	conf.load('pebble_sdk_common')
	if conf.options.timestamp:
		conf.env.TIMESTAMP=conf.options.timestamp
		conf.env.BUNDLE_NAME="app_{}.pbw".format(conf.env.TIMESTAMP)
	else:
		conf.env.BUNDLE_NAME="{}.pbw".format(conf.path.name)
	info_json_node=(conf.path.get_src().find_node('package.json')or conf.path.get_src().find_node('appinfo.json'))
	if info_json_node is None:
		conf.fatal('Could not find package.json')
	with open(info_json_node.abspath(),'r')as f:
		info_json=json.load(f)
	project_info=_extract_project_info(conf,info_json,info_json_node.name)
	conf.env.PROJECT_INFO=project_info
	conf.env.BUILD_TYPE='rocky'if project_info.get('projectType',None)=='rocky'else'app'
	if getattr(conf.env.PROJECT_INFO,'enableMultiJS',False):
		if not conf.env.WEBPACK:
			conf.fatal("'enableMultiJS' is set to true, but unable to locate webpack module at {} ""Please set enableMultiJS to false, or reinstall the SDK.".format(conf.env.NODE_PATH))
	if conf.env.BUILD_TYPE=='rocky':
		conf.find_program('node nodejs',var='NODE',errmsg="Unable to locate the Node command. ""Please check your Node installation and try again.")
		c_files=[c_file.path_from(conf.path.find_node('src'))for c_file in conf.path.ant_glob('src/**/*.c')]
		if c_files:
			Logs.pprint('YELLOW',"WARNING: C source files are not supported for Rocky.js ""projects. The following C files are being skipped: {}".format(c_files))
	if'resources'in project_info and'media'in project_info['resources']:
		conf.env.RESOURCES_JSON=project_info['resources']['media']
		if'publishedMedia'in project_info['resources']:
			conf.env.PUBLISHED_MEDIA_JSON=project_info['resources']['publishedMedia']
	conf.env.REQUESTED_PLATFORMS=project_info.get('targetPlatforms',[])
	conf.env.LIB_DIR="node_modules"
	get_target_platforms(conf)
	if'dependencies'in info_json:
		configure_libraries(conf,info_json['dependencies'])
	conf.load('process_message_keys')
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
		build_node=bld.path.get_bld().make_node(bld.env.BUILD_DIR)
		bld(rule=_generate_appinfo_c_file,target=build_node.make_node('appinfo.auto.c'),vars=['PROJECT_INFO'])
		bld(rule=_write_appinfo_json_file,target=bld.path.get_bld().make_node('appinfo.json'),vars=['PROJECT_INFO'])
		resource_node=None
		if bld.env.RESOURCES_JSON:
			try:
				resource_node=bld.path.find_node('resources')
			except AttributeError:
				bld.fatal("Unable to locate resources at resources/")
		if bld.env.BUILD_TYPE=='rocky':
			rocky_js_file=bld.path.find_or_declare('resources/rocky-app.js')
			rocky_js_file.parent.mkdir()
			bld.pbl_js_build(source=bld.path.ant_glob(['src/rocky/**/*.js','src/common/**/*.js']),target=rocky_js_file)
			resource_node=bld.path.get_bld().make_node('resources')
			bld.env.RESOURCES_JSON=[{'type':'js','name':'JS_SNAPSHOT','file':rocky_js_file.path_from(resource_node)}]
		resource_path=resource_node.path_from(bld.path)if resource_node else None
		generate_resources(bld,resource_path)
		if bld.env.BUILD_TYPE=='rocky':
			rocky_c_file=build_node.make_node('src/rocky.c')
			bld(rule='cp "${SRC}" "${TGT}"',source=find_sdk_component(bld,bld.env,'include/rocky.c'),target=rocky_c_file)
			if not bld.env.JS_TOOLING_SCRIPT:
				bld.fatal("Unable to locate tooling for this Rocky.js app build. Please ""try re-installing this version of the SDK.")
			bld.pbl_build(source=[rocky_c_file],target=build_node.make_node("pebble-app.elf"),bin_type='rocky')
	bld.env=cached_env
@conf
def pbl_program(self,*k,**kw):
	kw['bin_type']='app'
	kw['features']='c cprogram pebble_cprogram memory_usage'
	kw['app']=kw['target']
	kw['resources']=(self.path.find_or_declare(self.env.BUILD_DIR).make_node('app_resources.pbpack'))
	return self(*k,**kw)
@conf
def pbl_worker(self,*k,**kw):
	kw['bin_type']='worker'
	kw['features']='c cprogram pebble_cprogram memory_usage'
	kw['worker']=kw['target']
	return self(*k,**kw)
