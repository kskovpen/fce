import os, sys
import site
usersite = site.USER_SITE
sys.path.append(usersite+'/fce')
import objects as obj
import json
from optparse import OptionParser
import boost_histogram as bh
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
    parser.add_option("--target", default='tt', type=str, help="Target process [default: %default]")
    parser.add_option("--data", default='', type=str, help="Data location [default: %default]")
    parser.add_option("--dpi", default=192, type=int, help="DPI of the monitor [default: %default]")
    
    (options, args) = parser.parse_args(sys.argv[1:])
    
    return options

if __name__ == '__main__':
    
    options = main()
    
    f = open(usersite+'/fce/config/samples.json')
    samples = json.load(f)

    os.system("rm -rf "+hdir+"/output; mkdir "+hdir+"/output")

    for s in samples.keys():

        outHist = hist()
        outHist.create(options.bins, options.min, options.max)
        
        f = uproot.open(options.data+"/"+options.detector+"/"+options.energy.replace(' ', '')+"/"+s+".root")
        tr = f['ntuple']

        for arrays in tr.iterate(step_size='10 MB', library='np'):
            nev = len(arrays['electron_pt'])
            for i in range(nev):

                ev = obj.event(arrays, i)
                w = ev.w
        
                electrons, muons, leptons, jets, bjets, ljets = [], [], [], [], [], []
        
                for iel in range(len(arrays['electron_pt'][i])):
                    lep = obj.lepton(arrays, i, iel, 0)
                    electrons.append(lep)
                    leptons.append(lep)
                for imu in range(len(arrays['muon_pt'][i])):
                    lep = obj.lepton(arrays, i, imu, 1)
                    muons.append(lep)
                    leptons.append(lep)
                for ijet in range(len(arrays['jet_pt'][i])):
                    jet = obj.jet(arrays, i, ijet)
                    jets.append(jet)
                    if jet.isbtag:
                        bjets.append(jet)
                    else:
                        ljets.append(jet)
                
                nlep = len(leptons)
                nelectrons = len(electrons)
                nmuons = len(muons)
                njets = len(jets)
                nbjets = len(bjets)
            
                if not passevent: continue # selectionkey
            
                outHist.h['h'].fill(observable, weight=w) # observablekey

        outFile = uproot.recreate(hdir+"/output/"+s+".root")
        outFile['h'] = outHist.h['h']

    os.system('python3 '+usersite+'/fce/plot.py --energy=\"'+options.energy+'\" --detector=\"'+options.detector+'\"'+' --dpi=\"'+str(options.dpi)+'\"')

    os.system('python3 '+usersite+'/fce/fit.py --target=\"'+options.target+'\"')
