#! /usr/bin/env python
# encoding: utf-8
# WARNING! Do not edit! http://waf.googlecode.com/git/docs/wafbook/single.html#_obtaining_the_waf_file

import os
import time
import types
from waflib import Logs
from waflib.Configure import conf
from waflib.Task import Task
from waflib.TaskGen import after_method,before_method,feature
from waflib.Tools import c,c_preproc
import ldscript,process_bundle,process_headers,process_js,report_memory_usage,xcode_pebble
from pebble_sdk_platform import maybe_import_internal
from sdk_helpers import(append_to_attr,find_sdk_component,get_node_from_abspath,wrap_task_name_with_platform)
Task.__str__=wrap_task_name_with_platform
def options(opt):
	opt.load('gcc')
	opt.add_option('-d','--debug',action='store_true',default=False,dest='debug',help='Build in debug mode')
	opt.add_option('--no-groups',action='store_true',default=False,dest='no_groups')
	opt.add_option('--sandboxed-build',action='store_true',default=False,dest='sandbox')
def configure(conf):
	if not conf.options.debug:
		conf.env.append_value('DEFINES','RELEASE')
	else:
		Logs.pprint("CYAN","Debug enabled")
	if conf.options.no_groups:
		conf.env.USE_GROUPS=False
	else:
		conf.env.USE_GROUPS=True
	conf.env.SANDBOX=conf.options.sandbox
	conf.env.VERBOSE=conf.options.verbose
	conf.env.TIMESTAMP=int(time.time())
	pebble_sdk=conf.root.find_dir(os.path.dirname(__file__)).parent.parent.parent
	if pebble_sdk is None:
		conf.fatal("Unable to find Pebble SDK!\n""Please make sure you are running waf directly from your SDK.")
	conf.env.PEBBLE_SDK_ROOT=pebble_sdk.abspath()
	pebble_sdk_common=pebble_sdk.find_node('common')
	conf.env.PEBBLE_SDK_COMMON=pebble_sdk_common.abspath()
	if'NODE_PATH'in os.environ:
		conf.env.NODE_PATH=conf.root.find_node(os.environ['NODE_PATH']).abspath()
		webpack_path=conf.root.find_node(conf.env.NODE_PATH).find_node('.bin').abspath()
		try:
			conf.find_program('webpack',path_list=[webpack_path])
		except conf.errors.ConfigurationError:
			pass
	else:
		Logs.pprint('YELLOW',"WARNING: Unable to find $NODE_PATH variable required for SDK ""build. Please verify this build was initiated with a recent ""pebble-tool.")
	maybe_import_internal(conf.env)
def build(bld):
	bld.env=bld.all_envs['']
	bld.load('file_name_c_define')
	bld(features='message_keys')
	cached_env=bld.env
	for platform in bld.env.TARGET_PLATFORMS:
		bld.env=bld.all_envs[platform]
		if bld.env.USE_GROUPS:
			bld.add_group(bld.env.PLATFORM_NAME)
		build_node=bld.path.get_bld().find_or_declare(bld.env.BUILD_DIR)
		bld(features='subst',source=find_sdk_component(bld,bld.env,'pebble_app.ld.template'),target=build_node.make_node('pebble_app.ld.auto'),**bld.env.PLATFORM)
		js_tooling_script=find_sdk_component(bld,bld.env,'tools/generate_snapshot.js')
		bld.env.JS_TOOLING_SCRIPT=js_tooling_script if js_tooling_script else None
	bld.env=cached_env
	if bld.env.USE_GROUPS:
		bld.add_group('bundle')
def _wrap_c_preproc_scan(task):
	(nodes,names)=c_preproc.scan(task)
	if'pebble.h'in names:
		nodes.append(get_node_from_abspath(task.generator.bld,task.env.RESOURCE_ID_HEADER))
		nodes.append(get_node_from_abspath(task.generator.bld,task.env.MESSAGE_KEYS_HEADER))
	return nodes,names
@feature('c')
@before_method('process_source')
def setup_pebble_c(task_gen):
	platform=task_gen.env.PLATFORM_NAME
	append_to_attr(task_gen,'includes',[find_sdk_component(task_gen.bld,task_gen.env,'include'),'.','include','src'])
	append_to_attr(task_gen,'includes',platform)
	for lib in task_gen.bld.env.LIB_JSON:
		if'pebble'in lib:
			lib_include_node=task_gen.bld.path.find_node(lib['path']).find_node('include')
			append_to_attr(task_gen,'includes',[lib_include_node,lib_include_node.find_node(str(lib['name'])).find_node(platform)])
@feature('c')
@after_method('process_source')
def fix_pebble_h_dependencies(task_gen):
	for task in task_gen.tasks:
		if type(task)==c.c:
			task.scan=types.MethodType(_wrap_c_preproc_scan,task,c.c)
@feature('pebble_cprogram')
@before_method('process_source')
def setup_pebble_cprogram(task_gen):
	build_node=task_gen.path.get_bld().make_node(task_gen.env.BUILD_DIR)
	platform=task_gen.env.PLATFORM_NAME
	if not hasattr(task_gen,'bin_type')or getattr(task_gen,'bin_type')!='lib':
		append_to_attr(task_gen,'source',build_node.make_node('appinfo.auto.c'))
		append_to_attr(task_gen,'source',build_node.make_node('src/resource_ids.auto.c'))
		if task_gen.env.MESSAGE_KEYS:
			append_to_attr(task_gen,'source',get_node_from_abspath(task_gen.bld,task_gen.env.MESSAGE_KEYS_DEFINITION))
	append_to_attr(task_gen,'stlibpath',find_sdk_component(task_gen.bld,task_gen.env,'lib').abspath())
	append_to_attr(task_gen,'stlib','pebble')
	for lib in task_gen.bld.env.LIB_JSON:
		if not'pebble'in lib:
			continue
		binaries_path=task_gen.bld.path.find_node(lib['path']).find_node('binaries')
		if binaries_path:
			platform_binary_path=binaries_path.find_node(platform)
			if not platform_binary_path:
				task_gen.bld.fatal("Library {} is missing the {} platform folder in {}".format(lib['name'],platform,binaries_path))
			if lib['name'].startswith('@'):
				scoped_name=lib['name'].rsplit('/',1)
				lib_binary=(platform_binary_path.find_node(str(scoped_name[0])).find_node("lib{}.a".format(scoped_name[1])))
			else:
				lib_binary=platform_binary_path.find_node("lib{}.a".format(lib['name']))
			if not lib_binary:
				task_gen.bld.fatal("Library {} is missing a binary for the {} platform".format(lib['name'],platform))
			if lib['name'].startswith('@'):
				append_to_attr(task_gen,'stlibpath',platform_binary_path.find_node(str(scoped_name[0])).abspath())
				append_to_attr(task_gen,'stlib',scoped_name[1])
			else:
				append_to_attr(task_gen,'stlibpath',platform_binary_path.abspath())
				append_to_attr(task_gen,'stlib',lib['name'])
	append_to_attr(task_gen,'linkflags',['-Wl,--build-id=sha1','-Wl,-Map,pebble-{}.map,--emit-relocs'.format(getattr(task_gen,'bin_type','app'))])
	if not hasattr(task_gen,'ldscript'):
		task_gen.ldscript=(build_node.find_or_declare('pebble_app.ld.auto').path_from(task_gen.path))
def _get_entry_point(ctx,js_type,waf_js_entry_point):
	fallback_entry_point=waf_js_entry_point
	if not fallback_entry_point:
		if js_type=='pkjs':
			if ctx.path.find_node('src/pkjs/index.js'):
				fallback_entry_point='src/pkjs/index.js'
			else:
				fallback_entry_point='src/js/app.js'
		if js_type=='rockyjs':
			fallback_entry_point='src/rocky/index.js'
	project_info=ctx.env.PROJECT_INFO
	if not project_info.get('main'):
		return fallback_entry_point
	if project_info['main'].get(js_type):
		return str(project_info['main'][js_type])
	return fallback_entry_point
@conf
def pbl_bundle(self,*k,**kw):
	if kw.get('bin_type','app')=='lib':
		kw['features']='headers js package'
	else:
		if self.env.BUILD_TYPE=='rocky':
			kw['js_entry_file']=_get_entry_point(self,'pkjs',kw.get('js_entry_file'))
		kw['features']='js bundle'
	return self(*k,**kw)
@conf
def pbl_build(self,*k,**kw):
	valid_bin_types=('app','worker','lib','rocky')
	bin_type=kw.get('bin_type',None)
	if bin_type not in valid_bin_types:
		self.fatal("The pbl_build method requires that a valid bin_type attribute be specified. ""Valid options are {}".format(valid_bin_types))
	if bin_type=='rocky':
		kw['features']='c cprogram pebble_cprogram memory_usage'
	elif bin_type in('app','worker'):
		kw['features']='c cprogram pebble_cprogram memory_usage'
		kw[bin_type]=kw['target']
	elif bin_type=='lib':
		kw['features']='c cstlib memory_usage'
		path,name=kw['target'].rsplit('/',1)
		kw['lib']=self.path.find_or_declare(path).make_node("lib{}.a".format(name))
	if bin_type!='worker':
		kw['resources']=(self.env.PROJECT_RESBALL if bin_type=='lib'else self.path.find_or_declare(self.env.BUILD_DIR).make_node('app_resources.pbpack'))
	return self(*k,**kw)
@conf
def pbl_js_build(self,*k,**kw):
	kw['js_entry_file']=_get_entry_point(self,'rockyjs',kw.get('js_entry_file'))
	kw['features']='rockyjs'
	return self(*k,**kw)
