import os, sys, site, json
import uproot
import pyhf, cabinetry
from optparse import OptionParser

usersite = site.USER_SITE
home = os.path.expanduser('~')
hdir = home+'/.fce'

fname = hdir+'/fit.json'

def convert(target = 'tt'):
    
    fs = open(usersite+'/fce/config/samples.json')
    samples = json.load(fs)
    
    dc = {'channels': [{'name': 'ch1', 'samples': []}], 'observations': [], 'measurements': [], "version": "1.0.0"}
    f, h = {}, {}
    nbins, d = None, None
    for s in samples.keys():
        if s == 'New physics': continue
        f[s] = uproot.open(hdir+'/output/'+s+'.root')
        h[s] = f[s]['h']
        if not nbins: nbins = len(h[s].axis(0))
        data = [h[s].values()[ib] for ib in range(nbins)]
        if s != 'data':
            stat = [h[s].errors()[ib] for ib in range(nbins)]
            sample = {'name': s, 'data': data, 'modifiers': [{'name': 'prop_binch1', 'type': 'staterror', 'data': stat}]}
            if target == s: sample['modifiers'].append({'name': 'r_sig', 'type': 'normfactor', 'data': None})
            dc['channels'][0]['samples'].append(sample)
        else:
            d = data
            dc['observations'].append({'name': 'ch1', 'data': data})
        f[s].close()
    data = [0.01 if d[ib] != 0 else 0 for ib in range(nbins)]
    sample = {'name': 'np', 'data': data, 'modifiers': []}
    if target == 'New physics': sample['modifiers'].append({'name': 'r_sig', 'type': 'normfactor', 'data': None})
    dc['channels'][0]['samples'].append(sample)
    dc['measurements'] = [{'config': {'parameters': [{'bounds': [[-1000000, 1000000]], 'fixed': False, 'name': 'r_sig'}], 'poi': 'r_sig'}, 'name': 'meas'}]
    
    json_data = json.dumps(dc, indent=4)
    with open(fname, 'w') as outfile:
        outfile.write(json_data)
        
def main(argv = None):
    
    if argv == None:
        argv = sys.argv[1:]
        
    usage = "usage: %prog [options]\n Run fits"
                        
    parser = OptionParser(usage)
    parser.add_option("--target", default='tt', type=str, help="Name of the signal process [default: %default]")
    
    (options, args) = parser.parse_args(sys.argv[1:])
    
    return options

if __name__ == '__main__':
    
    options = main()

    os.system('rm -rf '+hdir+'/result.json')
    
    convert(options.target)
    
    df = json.load(open(fname))    
    ws = pyhf.Workspace(df)
    
    model, data = cabinetry.model_utils.model_and_data(ws)
    init_pars = model.config.suggested_init()
    bkg_pars = init_pars.copy()
    bkg_pars[model.config.poi_index] = 0
    if options.target == 'New physics':
        rsig = cabinetry.fit.significance(model, data, init_pars=bkg_pars)
        res = {'bestfit': None, 'uncertainty': None, 'observed_significance': rsig.observed_significance, 'expected_significance': None}
    else:
        rfit = cabinetry.fit.scan(model, data, 'r_sig', init_pars=init_pars)
        rsig = cabinetry.fit.significance(model, data, init_pars=init_pars)
        res = {'bestfit': rfit.bestfit, 'uncertainty': rfit.uncertainty, 'observed_significance': rsig.observed_significance, 'expected_significance': rsig.expected_significance}
    json_data = json.dumps(res, indent=4)
    with open(hdir+'/result.json', 'w') as outfile:
        outfile.write(json_data)
