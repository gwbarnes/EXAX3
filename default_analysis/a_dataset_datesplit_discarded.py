from __future__ import division

description = r'''
Extract anything discarded from a single dataset_datesplit.

Despite taking a previous (in case you want to use this in a chain) this
will not chain from source to previous.options.source.
'''

import a_dataset_datesplit
import dataset_typing
from extras import job_params, json_load, json_save
from dataset import Dataset
import blob

options = {
	'caption'                   : 'discarded from spilled dataset',
}
depend_extra = (a_dataset_datesplit, dataset_typing)

datasets = ('source', 'previous',)

def prepare():
	source_params = job_params(datasets.source)
	return a_dataset_datesplit.real_prepare(datasets.source, datasets.previous, source_params.options)

def analysis(sliceno, prepare_res):
	stats = {}
	prev_spilldata = blob.load('spilldata', jobid=datasets.source, sliceno=sliceno)
	source_params = job_params(datasets.source)
	for source, data in prev_spilldata:
		_, stats[source] = a_dataset_datesplit.process_one(sliceno, source_params.options, source, prepare_res, data, save_discard=True)
	source_params = job_params(datasets.source)
	prev_params = job_params(source_params.datasets.previous, default_empty=True)
	for source in Dataset(source_params.datasets.source).chain(stop_jobid=prev_params.datasets.source):
		_, stats[source] = a_dataset_datesplit.process_one(sliceno, source_params.options, source, prepare_res, save_discard=True)
	blob.save(stats, 'stats', sliceno=sliceno, temp=False)

def synthesis(params, prepare_res):
	source_params = job_params(datasets.source)
	source_params.options.caption = options.caption
	a_dataset_datesplit.real_synthesis(params, source_params.options, source_params.datasets, 0, prepare_res, False, save_discard=True)
	stats = json_load()
	json_save(dict(
		minmax              = stats.minmax_discarded,
		included_lines      = stats.discarded_lines,
		split_date          = stats.split_date,
		discard_before_date = stats.discard_before_date,
	))
