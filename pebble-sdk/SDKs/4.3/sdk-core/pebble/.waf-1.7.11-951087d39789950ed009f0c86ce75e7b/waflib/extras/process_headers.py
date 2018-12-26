#! /usr/bin/env python
# encoding: utf-8
# WARNING! Do not edit! http://waf.googlecode.com/git/docs/wafbook/single.html#_obtaining_the_waf_file

from waflib.TaskGen import before_method,feature
from waflib import Context,Task
from sdk_helpers import get_node_from_abspath
@feature('headers')
@before_method('make_lib_bundle')
def process_headers(task_gen):
	header_nodes=task_gen.to_nodes(task_gen.includes)
	for platform in task_gen.env.TARGET_PLATFORMS:
		env=task_gen.bld.all_envs[platform]
		header_nodes.append(get_node_from_abspath(task_gen.bld,env['RESOURCE_ID_HEADER']))
	if'MESSAGE_KEYS_HEADER'in dict(task_gen.env):
		header_nodes.append(get_node_from_abspath(task_gen.bld,task_gen.env['MESSAGE_KEYS_HEADER']))
	lib_name=str(task_gen.env.PROJECT_INFO['name'])
	lib_include_node=task_gen.bld.path.get_bld().make_node('include').make_node(lib_name)
	target_nodes=[]
	for header in header_nodes:
		base_node=(task_gen.bld.path.get_bld()if header.is_child_of(task_gen.bld.path.get_bld())else task_gen.bld.path)
		if header.is_child_of(base_node.find_node('include')):
			header_path=header.path_from(base_node.find_node('include'))
		else:
			header_path=header.path_from(base_node)
		target_node=lib_include_node.make_node(header_path)
		target_node.parent.mkdir()
		target_nodes.append(target_node)
	task_gen.includes=target_nodes
	task_gen.create_task('copy_headers',src=header_nodes,tgt=target_nodes)
@Task.update_outputs
class copy_headers(Task.Task):
	def run(self):
		bld=self.generator.bld
		if len(self.inputs)!=len(self.outputs):
			bld.fatal("Number of input headers ({}) does not match number of target headers ({})".format(len(self.inputs),len(self.outputs)))
		for i in range(len(self.inputs)):
			bld.cmd_and_log('cp "{src}" "{tgt}"'.format(src=self.inputs[i].abspath(),tgt=self.outputs[i].abspath()),quiet=Context.BOTH)
