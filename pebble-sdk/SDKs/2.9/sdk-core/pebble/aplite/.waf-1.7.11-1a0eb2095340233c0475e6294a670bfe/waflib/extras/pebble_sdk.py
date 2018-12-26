#! /usr/bin/env python
# encoding: utf-8
# WARNING! Do not edit! http://waf.googlecode.com/git/docs/wafbook/single.html#_obtaining_the_waf_file

import json
import os
import sys
import time
import waflib.extras.inject_metadata as inject_metadata
import waflib.extras.ldscript as ldscript
import waflib.extras.mkbundle as mkbundle
import waflib.extras.objcopy as objcopy
import waflib.extras.c_preproc as c_preproc
import waflib.extras.xcode_pebble
import waflib.extras.pebble_sdk_gcc as pebble_sdk_gcc
from waflib import Logs
from waflib.TaskGen import before_method,feature
SDK_VERSION={'major':5,'minor':0}
def options(opt):
	opt.load('gcc')
	opt.add_option('-d','--debug',action='store_true',default=False,dest='debug',help='Build in debug mode')
	opt.add_option('-t','--timestamp',dest='timestamp',help="Use a specific timestamp to label this package (ie, your repository's last commit time), defaults to time of build")
def configure(conf):
	pebble_sdk_gcc.configure(conf)
	if not conf.options.debug:
		conf.env.append_value('DEFINES','RELEASE')
	else:
		print"Debug enabled"
	pebble_sdk=conf.root.find_dir(os.path.dirname(__file__)).parent.parent.parent
	if pebble_sdk is None:
		conf.fatal("Unable to find Pebble SDK!\n"+"Please make sure you are running waf directly from your SDK.")
	sdk_check_nodes=['lib/libpebble.a','pebble_app.ld','tools','include','include/pebble.h']
	for n in sdk_check_nodes:
		if pebble_sdk.find_node(n)is None:
			conf.fatal("Invalid SDK - Could not find {}".format(n))
	print"Found Pebble SDK in\t\t\t : {}".format(pebble_sdk.abspath())
	conf.env.PEBBLE_SDK=pebble_sdk.abspath()
def build(bld):
	c_preproc.enable_file_name_c_define()
	appinfo_json_node=bld.path.get_src().find_node('appinfo.json')
	if appinfo_json_node is None:
		bld.fatal('Could not find appinfo.json')
	import waflib.extras.generate_appinfo as generate_appinfo
	def _generate_appinfo_c_file(bld,appinfo_json_node,appinfo_c_node):
		def _generate_appinfo_c_file_rule(task):
			generate_appinfo.generate_appinfo(task.inputs[0].abspath(),task.outputs[0].abspath())
		bld(rule=_generate_appinfo_c_file_rule,source=appinfo_json_node,target=appinfo_c_node)
	appinfo_c_node=bld.path.get_bld().make_node('appinfo.auto.c')
	_generate_appinfo_c_file(bld,appinfo_json_node,appinfo_c_node)
	import waflib.extras.process_resources as process_resources
	def _generate_resources(bld,appinfo_json_node,sdk_folder):
		resource_id_header=bld.path.get_bld().make_node('src/resource_ids.auto.h')
		with open(appinfo_json_node.abspath(),'r')as f:
			appinfo=json.load(f)
		resources_dict=appinfo['resources']
		process_resources.gen_resource_deps(bld,resources_dict=resources_dict,resources_path_node=bld.path.get_src().find_node('resources'),output_pack_node=bld.path.get_bld().make_node('app_resources.pbpack'),output_id_header_node=resource_id_header,output_version_header_node=None,resource_header_path="pebble.h",tools_path=sdk_folder.find_dir('tools'))
	sdk_folder=bld.root.find_dir(bld.env['PEBBLE_SDK'])
	_generate_resources(bld,appinfo_json_node,sdk_folder)
def append_to_attr(self,attr,new_values):
	values=self.to_list(getattr(self,attr,[]))
	values.extend(new_values)
	setattr(self,attr,values)
def setup_pebble_cprogram(self,name):
	sdk_folder=self.bld.root.find_dir(self.bld.env['PEBBLE_SDK'])
	append_to_attr(self,'source',[self.bld.path.get_bld().make_node('appinfo.auto.c')])
	append_to_attr(self,'stlibpath',[sdk_folder.find_dir('lib').abspath()])
	append_to_attr(self,'stlib',['pebble'])
	append_to_attr(self,'linkflags',['-Wl,-Map,pebble-%s.map,--emit-relocs'%(name)])
	if not getattr(self,'ldscript',None):
		setattr(self,'ldscript',sdk_folder.find_node('pebble_app.ld').path_from(self.bld.path))
@feature('c')
@before_method('process_source')
def setup_pebble_c(self):
	sdk_folder=self.bld.root.find_dir(self.bld.env['PEBBLE_SDK'])
	append_to_attr(self,'includes',[sdk_folder.find_dir('include').path_from(self.bld.path),'.','src'])
	append_to_attr(self,'cflags',['-fPIE'])
@feature('cprogram')
@before_method('process_source')
def setup_cprogram(self):
	append_to_attr(self,'linkflags',['-mcpu=cortex-m3','-mthumb','-fPIE'])
@feature('cprogram_pebble_app')
@before_method('process_source')
def setup_pebble_app_cprogram(self):
	setup_pebble_cprogram(self,'app')
@feature('cprogram_pebble_worker')
@before_method('process_source')
def setup_pebble_worker_cprogram(self):
	setup_pebble_cprogram(self,'worker')
@feature('pbl_bundle')
def make_pbl_bundle(self):
	timestamp=self.bld.options.timestamp
	pbw_basename='app_'+str(timestamp)if timestamp else self.bld.path.name
	if timestamp is None:
		timestamp=int(time.time())
	app_elf_file=self.bld.path.get_bld().make_node(getattr(self,'elf'))
	if app_elf_file is None:
		raise Exception("Must specify elf argument to pbl_bundle")
	app_raw_bin_file=self.bld.path.get_bld().make_node('pebble-app.raw.bin')
	self.bld(rule=objcopy.objcopy_bin,source=app_elf_file,target=app_raw_bin_file)
	worker_elf_file=getattr(self,'worker_elf',None)
	if worker_elf_file is not None:
		worker_elf_file=self.bld.path.get_bld().make_node(worker_elf_file)
		worker_raw_bin_file=self.bld.path.get_bld().make_node('pebble-worker.raw.bin')
		self.bld(rule=objcopy.objcopy_bin,source=worker_elf_file,target=worker_raw_bin_file)
	js_nodes=self.to_nodes(getattr(self,'js',[]))
	js_files=[x.abspath()for x in js_nodes]
	has_jsapp=len(js_nodes)>0
	resources_file=self.bld.path.get_bld().make_node('app_resources.pbpack.data')
	app_bin_file=self.bld.path.get_bld().make_node('pebble-app.bin')
	pebble_sdk_gcc.gen_inject_metadata_rule(self.bld,src_bin_file=app_raw_bin_file,dst_bin_file=app_bin_file,elf_file=app_elf_file,resource_file=resources_file,timestamp=timestamp,has_jsapp=has_jsapp,has_worker=(worker_elf_file is not None))
	if worker_elf_file is not None:
		worker_bin_file=self.bld.path.get_bld().make_node('pebble-worker.bin')
		pebble_sdk_gcc.gen_inject_metadata_rule(self.bld,src_bin_file=worker_raw_bin_file,dst_bin_file=worker_bin_file,elf_file=worker_elf_file,resource_file=None,timestamp=timestamp,has_jsapp=has_jsapp,has_worker=(worker_elf_file is not None))
		worker_nodes=[worker_bin_file]
		worker_bin_file_abs_path=worker_bin_file.abspath()
	else:
		worker_nodes=[]
		worker_bin_file_abs_path=None
	resources_pack=self.bld.path.get_bld().make_node('app_resources.pbpack')
	pbz_output=self.bld.path.get_bld().make_node(pbw_basename+'.pbw')
	def make_watchapp_bundle(task):
		watchapp=task.inputs[0].abspath()
		resources=task.inputs[1].abspath()
		outfile=task.outputs[0].abspath()
		return mkbundle.make_watchapp_bundle(appinfo=self.bld.path.get_src().find_node('appinfo.json').abspath(),js_files=js_files,watchapp=watchapp,watchapp_timestamp=timestamp,sdk_version=SDK_VERSION,resources=resources,resources_timestamp=timestamp,worker_bin=worker_bin_file_abs_path,outfile=outfile)
	self.bld(rule=make_watchapp_bundle,source=[app_bin_file,resources_pack]+js_nodes+worker_nodes,target=pbz_output)
	def report_memory_usage(task):
		src_path=task.inputs[0].abspath()
		size_output=task.generator.bld.cmd_and_log([task.env.SIZE,src_path],quiet=waflib.Context.BOTH,output=waflib.Context.STDOUT)
		text_size,data_size,bss_size=[int(x)for x in size_output.splitlines()[1].split()[:3]]
		app_ram_size=data_size+bss_size+text_size
		if task.generator.type=='app':
			max_ram=inject_metadata.MAX_APP_MEMORY_SIZE
		else:
			max_ram=inject_metadata.MAX_WORKER_MEMORY_SIZE
		free_size=max_ram-app_ram_size
		Logs.pprint('YELLOW',"%s memory usage:\n=============\n""Total footprint in RAM:         %6u bytes / ~%ukb\n""Free RAM available (heap):      %6u bytes\n"%(task.generator.type,app_ram_size,max_ram/1024,free_size))
	self.bld(rule=report_memory_usage,name='report-memory-usage',source=[app_elf_file],type="app",target=None)
	if worker_elf_file is not None:
		self.bld(rule=report_memory_usage,name='report-memory-usage',source=[worker_elf_file],type="worker",target=None)
from waflib.Configure import conf
@conf
def pbl_bundle(self,*k,**kw):
	kw['features']='pbl_bundle'
	return self(*k,**kw)
@conf
def pbl_program(self,*k,**kw):
	kw['features']='c cprogram cprogram_pebble_app'
	return self(*k,**kw)
@conf
def pbl_worker(self,*k,**kw):
	kw['features']='c cprogram cprogram_pebble_worker'
	return self(*k,**kw)
