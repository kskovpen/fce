import os, sys
import site
usersite = site.USER_SITE
sys.path.append(usersite+'/fce')
import objects as obj
import json
from optparse import OptionParser
import boost_histogram as bh
import numpy as np
import uproot

home = os.path.expanduser('~')
hdir = home+'/.fce'

class hist:

    def __init__(self):
        
        self.var = ['h']
        self.h = {}
        
    def create(self, bins, min, max):

        for v in self.var:
            hname = v
            self.h[hname] = bh.Histogram(bh.axis.Regular(bins, min, max))

def main(argv = None):
    
    if argv == None:
        argv = sys.argv[1:]
        
    usage = "usage: %prog [options]\n Run analysis"
    
    parser = OptionParser(usage)
    parser.add_option("--bins", default=5, type=int, help="Number of bins [default: %default]")
    parser.add_option("--min", default=0.0, type=float, help="Histogram min range value [default: %default]")
    parser.add_option("--max", default=5.0, type=float, help="Histogram max range value [default: %default]")
    parser.add_option("--energy", default='365 GeV', type=str, help="Collision energy [default: %default]")
    parser.add_option("--detector", default='IDEA', type=str, help="Detector name [default: %default]")
    parser.add_option("--target", default='None', type=str, help="Target process [default: %default]")
    parser.add_option("--data", default='', type=str, help="Data location [default: %default]")
    parser.add_option("--dpi", default=192, type=int, help="DPI of the monitor [default: %default]")
    parser.add_option("--doskim", action='store_true', help="Prepare a skim of events [default: %default]")
    parser.add_option("--useskim", action='store_true', help="Use a skim of events [default: %default]")
    
    (options, args) = parser.parse_args(sys.argv[1:])
    
    return options

if __name__ == '__main__':
    
    options = main()
    
    f = open(usersite+'/fce/config/samples.json')
    samples = json.load(f)

    os.system("rm -rf "+hdir+"/output; mkdir "+hdir+"/output")

    if options.doskim: 
        os.system('rm -rf '+hdir+'/skim')
        skimdir = hdir+"/skim/"+options.detector+"/"+options.energy.replace(' ', '')
        os.system('mkdir -p '+skimdir)    
    
    en = options.energy.replace(' GeV', '')
        
    for s in samples[en].keys():

        outHist = hist()
        outHist.create(options.bins, options.min, options.max)
        
        if options.useskim:
            f = uproot.open(hdir+"/skim/"+options.detector+"/"+options.energy.replace(' ', '')+"/"+s+".root")
        else:
            f = uproot.open(options.data+"/"+options.detector+"/"+options.energy.replace(' ', '')+"/"+s+".root")
        tr = f['ntuple']
        ex = []
        for k in tr.keys():
            b = tr[k].basket(0).raw_data
            if type(b) != np.ndarray: ex.append(k)
        l = [k for k in tr.keys() if k not in ex]
        
        if options.doskim: arrw = {k:[] for k in tr.keys()}
        
        for arrays in tr.iterate(l, step_size='10 MB', library='np'):
            nev = len(arrays['weight'])
            for i in range(nev):

                ev = obj.event(arrays, i)
                w = ev.w
                
                MET = obj.MET(arrays, i)
        
                electrons, muons, leptons, jets, bjets, ljets, photons = [], [], [], [], [], [], []
                
                if 'electron_pt' in arrays.keys():
                    for iel in range(len(arrays['electron_pt'][i])):
                        lep = obj.lepton(arrays, i, iel, 0)
                        electrons.append(lep)
                        leptons.append(lep)
                if 'muon_pt' in arrays.keys():
                    for imu in range(len(arrays['muon_pt'][i])):
                        lep = obj.lepton(arrays, i, imu, 1)
                        muons.append(lep)
                        leptons.append(lep)
                if 'jet_pt' in arrays.keys():
                    for ijet in range(len(arrays['jet_pt'][i])):
                        jet = obj.jet(arrays, i, ijet)
                        jets.append(jet)
                if 'photon_pt' in arrays.keys():
                    for ipho in range(len(arrays['photon_pt'][i])):
                        pho = obj.photon(arrays, i, ipho)
                        photons.append(pho)
                
                nlep = len(leptons)
                nelectrons = len(electrons)
                nmuons = len(muons)
                njets = len(jets)
                nphotons = len(photons)
                
                if not skim: continue # skimkey
                
                if options.doskim:
                    for k in arrays.keys(): arrw[k].append(arrays[k][i])
            
                if not passevent: continue # selectionkey

                outHist.h['h'].fill(observable, weight=w) # observablekey

        outFile = uproot.recreate(hdir+"/output/"+s+".root")
        outFile['h'] = outHist.h['h']
        
        if options.doskim:
            fs = uproot.recreate(skimdir+"/"+s+".root")
            fs['ntuple'] = arrw

    os.system('python3 '+usersite+'/fce/plot.py --energy=\"'+options.energy+'\" --detector=\"'+options.detector+'\"'+' --dpi=\"'+str(options.dpi)+'\"')

    if options.target != 'None': os.system('python3 '+usersite+'/fce/fit.py --target=\"'+options.target+'\"')
