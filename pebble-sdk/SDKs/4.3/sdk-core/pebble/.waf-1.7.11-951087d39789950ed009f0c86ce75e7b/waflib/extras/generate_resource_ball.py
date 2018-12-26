#! /usr/bin/env python
# encoding: utf-8
# WARNING! Do not edit! http://waf.googlecode.com/git/docs/wafbook/single.html#_obtaining_the_waf_file

from waflib import Node,Task,TaskGen
from resources.resource_map import resource_generator
from resources.resource_map.resource_generator_js import JsResourceGenerator
from resources.types.resource_definition import StorageType
from resources.types.resource_object import ResourceObject
from resources.types.resource_ball import ResourceBall
class reso(Task.Task):
	def run(self):
		reso=resource_generator.generate_object(self,self.definition)
		reso.dump(self.outputs[0])
@Task.update_outputs
class resource_ball(Task.Task):
	def run(self):
		resos=[ResourceObject.load(r.abspath())for r in self.inputs]
		resource_id_mapping=getattr(self.env,'RESOURCE_ID_MAPPING',{})
		ordered_resos=[]
		if not resource_id_mapping:
			for s in[StorageType.pbpack,StorageType.builtin,StorageType.pfs]:
				ordered_resos.extend((o for o in resos if o.definition.storage==s))
		else:
			resos_dict={resource_id_mapping[reso.definition.name]:reso for reso in resos}
			ordered_resos=[resos_dict[x]for x in range(1,len(resos)+1)]
		res_ball=ResourceBall(ordered_resos,getattr(self,'resource_declarations',[]))
		res_ball.dump(self.outputs[0])
def process_resource_definition(task_gen,resource_definition):
	sources=[]
	for s in resource_definition.sources:
		source_node=task_gen.path.make_node(s)
		if source_node is None:
			task_gen.bld.fatal("Could not find resource at %s"%task_gen.bld.path.find_node(s).abspath())
		sources.append(source_node)
	output_name='%s.%s.%s'%(sources[0].relpath(),str(resource_definition.name),'reso')
	output=task_gen.resource_ball.parent.make_node(output_name)
	task=task_gen.create_task('reso',sources,output)
	task.definition=resource_definition
	task.dep_nodes=getattr(task_gen,'resource_dependencies',[])
	if resource_definition.type=='js'and'PEBBLE_SDK_ROOT'in task_gen.env:
		task_gen.bld.all_envs[task_gen.env.PLATFORM_NAME].JS_RESO=output
	return output
@TaskGen.feature('generate_resource_ball')
@TaskGen.before_method('process_source','process_rule')
def process_resource_ball(task_gen):
	resource_objects=[]
	bundled_resos=[]
	for r in task_gen.resources:
		if isinstance(r,Node.Node):
			resource_objects.append(r)
		else:
			processed_resource=process_resource_definition(task_gen,r)
			resource_objects.append(processed_resource)
			bundled_resos.append(processed_resource)
	if getattr(task_gen,'project_resource_ball',None):
		prb_task=task_gen.create_task('resource_ball',bundled_resos,task_gen.project_resource_ball)
		prb_task.dep_node=getattr(task_gen,'resource_dependencies',[])
		prb_task.dep_vars=getattr(task_gen,'vars',[])
	task=task_gen.create_task('resource_ball',resource_objects,task_gen.resource_ball)
	task.resource_declarations=getattr(task_gen,'resource_declarations',[])
	task.dep_nodes=getattr(task_gen,'resource_dependencies',[])
	task.dep_vars=getattr(task_gen,'vars',[])
