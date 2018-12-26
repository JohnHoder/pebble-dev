#! /usr/bin/env python
# encoding: utf-8
# WARNING! Do not edit! http://waf.googlecode.com/git/docs/wafbook/single.html#_obtaining_the_waf_file

import json
import os
import subprocess
from string import Template
from waflib.Errors import WafError
from waflib.TaskGen import before_method,feature
from waflib import Context,Logs,Node,Task
from sdk_helpers import find_sdk_component,get_node_from_abspath
from sdk_helpers import process_package
@feature('rockyjs')
@before_method('process_sdk_resources')
def process_rocky_js(task_gen):
	bld=task_gen.bld
	task_gen.mappings={'':(lambda task_gen,node:None)}
	js_nodes=task_gen.to_nodes(task_gen.source)
	target=task_gen.to_nodes(task_gen.target)
	if not js_nodes:
		task_gen.bld.fatal("Project does not contain any source code.")
	js_nodes.append(find_sdk_component(bld,task_gen.env,'include/rocky.js'))
	node_modules=[]
	rocky_linter=None
	if bld.path.find_node('node_modules'):
		node_modules.append(bld.path.find_node('node_modules'))
	if bld.env.NODE_PATH:
		node_modules.append(bld.root.find_node(bld.env.NODE_PATH))
	for node_modules_node in node_modules:
		rocky_linter=node_modules_node.ant_glob('rocky-lint/**/rocky-lint.js')
		if rocky_linter:
			rocky_linter=rocky_linter[0]
			break
	rocky_definitions=find_sdk_component(bld,task_gen.env,'tools/rocky-lint/rocky.d.ts')
	if rocky_linter and rocky_definitions:
		lintable_nodes=[node for node in js_nodes if node.is_child_of(bld.path)]
		lint_task=task_gen.create_task('lint_js',src=lintable_nodes)
		lint_task.linter=[task_gen.env.NODE,rocky_linter.path_from(bld.path),'-d',rocky_definitions.path_from(bld.path)]
	else:
		Logs.pprint('YELLOW',"Rocky JS linter not present - skipping lint task")
	merge_task=task_gen.create_task('merge_js',src=js_nodes,tgt=target)
	merge_task.js_entry_file=task_gen.js_entry_file
	merge_task.js_build_type='rocky'
@feature('js')
@before_method('make_pbl_bundle','make_lib_bundle')
def process_js(task_gen):
	js_nodes=task_gen.to_nodes(getattr(task_gen,'js',[]))
	if not js_nodes:
		return
	if task_gen.env.PROJECT_INFO.get('enableMultiJS',False):
		target_js=task_gen.bld.path.get_bld().make_node('pebble-js-app.js')
		target_js_map=target_js.change_ext('.js.map')
		task_gen.js=[target_js,target_js_map]
		merge_task=task_gen.create_task('merge_js',src=js_nodes,tgt=[target_js,target_js_map])
		merge_task.js_entry_file=task_gen.js_entry_file
		merge_task.js_build_type='pkjs'
		merge_task.js_source_map_config={'sourceMapFilename':target_js_map.name}
		return
	if task_gen.env.BUILD_TYPE!='lib':
		for node in js_nodes:
			if'pebble-js-app.js'in node.abspath():
				break
		else:
			Logs.pprint("CYAN","WARNING: enableMultiJS is not enabled for this project and ""pebble-js-app.js does not exist")
	js_nodes_to_copy=[js_node for js_node in js_nodes if not js_node.is_bld()]
	if not js_nodes_to_copy:
		task_gen.js=js_nodes
		return
	target_nodes=[]
	for js in js_nodes_to_copy:
		if js.is_child_of(task_gen.bld.path.find_node('src')):
			js_path=js.path_from(task_gen.bld.path.find_node('src'))
		else:
			js_path=os.path.abspath(js.path_from(task_gen.bld.path))
		target_node=task_gen.bld.path.get_bld().make_node(js_path)
		target_node.parent.mkdir()
		target_nodes.append(target_node)
	task_gen.js=target_nodes+list(set(js_nodes)-set(js_nodes_to_copy))
	task_gen.create_task('copy_js',src=js_nodes_to_copy,tgt=target_nodes)
class copy_js(Task.Task):
	def run(self):
		bld=self.generator.bld
		if len(self.inputs)!=len(self.outputs):
			bld.fatal("Number of input JS files ({}) does not match number of target JS files ({})".format(len(self.inputs),len(self.outputs)))
		for i in range(len(self.inputs)):
			bld.cmd_and_log('cp "{src}" "{tgt}"'.format(src=self.inputs[i].abspath(),tgt=self.outputs[i].abspath()),quiet=Context.BOTH)
class merge_js(Task.Task):
	def run(self):
		bld=self.generator.bld
		js_build_type=getattr(self,'js_build_type')
		js_nodes=self.inputs
		entry_point=bld.path.find_resource(self.js_entry_file)
		if entry_point not in js_nodes:
			bld.fatal("\n\nJS entry file '{}' not found in JS source files '{}'. We expect to find ""a javascript file here that we will execute directly when your app launches.""\n\nIf you are an advanced user, you can supply the 'js_entry_file' ""parameter to 'pbl_bundle' in your wscript to change the default entry point."" Note that doing this will break CloudPebble compatibility.".format(self.js_entry_file,js_nodes))
		target_js=self.outputs[0]
		entry=[entry_point.abspath()]
		if js_build_type=='pkjs':
			entry.insert(0,"_pkjs_shared_additions.js")
			if self.env.BUILD_TYPE=='rocky':
				entry.insert(1,"_pkjs_message_wrapper.js")
		common_node=bld.root.find_node(self.generator.env.PEBBLE_SDK_COMMON)
		tools_webpack_node=common_node.find_node('tools').find_node('webpack')
		webpack_config_template_node=tools_webpack_node.find_node('webpack-config.js.pytemplate')
		with open(webpack_config_template_node.abspath())as f:
			webpack_config_template_content=f.read()
		search_paths=[common_node.find_node('include').abspath(),tools_webpack_node.abspath(),bld.root.find_node(self.generator.env.NODE_PATH).abspath(),bld.path.get_bld().make_node('js').abspath()]
		pebble_packages=[str(lib['name'])for lib in bld.env.LIB_JSON if'pebble'in lib]
		aliases={lib:"{}/dist/js".format(lib)for lib in pebble_packages}
		info_json_file=bld.path.find_node('package.json')or bld.path.find_node('appinfo.json')
		if info_json_file:
			aliases.update({'app_package.json':info_json_file.abspath()})
		config_file=(bld.path.get_bld().make_node("webpack/{}/webpack.config.js".format(js_build_type)))
		config_file.parent.mkdir()
		with open(config_file.abspath(),'w')as f:
			m={'IS_SANDBOX':bool(self.env.SANDBOX),'ENTRY_FILENAMES':entry,'OUTPUT_PATH':target_js.parent.path_from(bld.path),'OUTPUT_FILENAME':target_js.name,'RESOLVE_ROOTS':search_paths,'RESOLVE_ALIASES':aliases,'SOURCE_MAP_CONFIG':getattr(self,'js_source_map_config',None)}
			f.write(Template(webpack_config_template_content).substitute({k:json.dumps(m[k],separators=(',\n',': '))for k in m}))
		cmd=("'{webpack}' --config {config} --display-modules".format(webpack=self.generator.env.WEBPACK,config=config_file.path_from(bld.path)))
		try:
			out=bld.cmd_and_log(cmd,quiet=Context.BOTH,output=Context.STDOUT)
		except WafError ,e:
			bld.fatal("JS bundling failed\n{}\n{}".format(e.stdout,e.stderr))
		else:
			if self.env.VERBOSE>0:
				Logs.pprint('WHITE',out)
class lint_js(Task.Task):
	def run(self):
		self.name='lint_js'
		js_nodes=self.inputs
		for js_node in js_nodes:
			cmd=self.linter+[js_node.path_from(self.generator.bld.path)]
			proc=subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
			out,err=proc.communicate()
			if err:
				Logs.pprint('CYAN',"\n========== Lint Results: {} ==========\n".format(js_node))
				Logs.pprint('WHITE',"{}\n{}\n".format(out,err))
				if proc.returncode!=0:
					self.generator.bld.fatal("Project failed linting.")
