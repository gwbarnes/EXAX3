from random import randint
from collections import OrderedDict, defaultdict
from itertools import combinations
from copy import deepcopy

import setupfile
import deptree
from extras import job_params

def find_possible_jobs(db, methods, job):
    method = job['method']
    params = {method: job['params'][method]}
    optset = methods.params2optset(params)
    def inner():
        for uid, jobid in db.match_exact([(method, 0, optset,)]):
            yield jobid, ()
            return # no depjobs is enough - stop
        for remset in combinations(optset, remcount):
            for uid, jobid in db.match_complex([(method, 0, optset - set(remset),)]):
                yield jobid, remset
    res = {}
    remcount = 0
    while not res:
        remcount += 1
        if remcount == len(optset):
            break
        for jobid, remset in inner():
            remset = tuple(s.split()[1] for s in remset)
            res[jobid] = remset
    return dict(_job_candidates_options(res))

def _job_candidates_options(candidates):
    for jobid, remset in candidates.iteritems():
        setup = job_params(jobid)
        optdiff = defaultdict(dict)
        for thing in remset:
            section, name = thing.split('-', 1)
            optdiff[section][name] = setup[section][name]
        yield jobid, optdiff

def initialise_jobs(setup, target_WorkSpace, DataBase, Methods, verbose=False):

    # create a DepTree object used to track options and make status
    DepTree = deptree.DepTree(Methods, setup)

    # compare database to deptree
    reqlist = DepTree.get_reqlist()
    for uid, jobid in DataBase.match_exact(reqlist):
        DepTree.set_link(uid, jobid)
    DepTree.propagate_make()
    if setup.why_build:
        orig_tree = deepcopy(DepTree.tree)
    DepTree.fill_in_default_options()

    # get list of jobs in execution order
    joblist = DepTree.get_sorted_joblist()
    newjoblist = filter(lambda x:x['make']==True, joblist)
    num_new_jobs = len(newjoblist)

    if setup.why_build == True or (setup.why_build and num_new_jobs):
        res = OrderedDict()
        DepTree.tree = orig_tree
        joblist = DepTree.get_sorted_joblist()
        for job in joblist:
            if job['make']:
                res[job['method']] = find_possible_jobs(DataBase, Methods, job)
            else:
                res[job['method']] = {job['link']: {}}
        return [], {'why_build': res}

    if num_new_jobs:
        new_jobid_list = target_WorkSpace.allocate_jobs(num_new_jobs)
        # insert new jobids
        for (x,jid) in zip(newjoblist, new_jobid_list):
            x['link'] = jid
        for data in newjoblist:
            new_setup = setupfile.generate(
                setup.caption,
                data['method'],
                data['params'],
                {dep: DepTree.get_link(dep) for dep in data['dep']},
                package = Methods.db[data['method']]['package']
                )
            new_setup.hash = Methods.hash[data['method']][0]
            new_setup.seed = randint(0, 2**63 - 1)
            new_setup.jobid = data['link']
            new_setup.slices = target_WorkSpace.get_slices()
            typing = {}
            for method in data['params']:
                m_typing = Methods.typing[method]
                if m_typing:
                    typing[method] = m_typing
            if typing:
                new_setup._typing = typing
            setupfile.save_setup(data['link'], new_setup)
    else:
        new_jobid_list = []

    res = {j['method']: {'link': j['link'], 'make': j['make']} for j in joblist}
    return new_jobid_list, {'jobs': res}
