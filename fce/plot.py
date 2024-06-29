import os, sys, datetime
from optparse import OptionParser
import uproot, json, site
import matplotlib.pyplot as plt
import mplhep as hep

usersite = site.USER_SITE
home = os.path.expanduser('~')
hdir = home+'/.fce'

hep.style.use(hep.style.ROOT)

def main(argv = None):
    
    if argv == None:
        argv = sys.argv[1:]
        
    usage = "usage: %prog [options]\n Plot results"
    
    parser = OptionParser(usage)
    parser.add_option("--energy", default='365 GeV', type=str, help="Collision energy [default: %default]")
    parser.add_option("--detector", default='IDEA', type=str, help="Detector name [default: %default]")
    parser.add_option("--dpi", default=192, type=int, help="DPI of the monitor [default: %default]")
    
    (options, args) = parser.parse_args(sys.argv[1:])
    
    return options

if __name__ == '__main__':
    
    options = main()
            
    f = open(usersite+'/fce/config/samples.json')
    samples = json.load(f)

    cols = [(63/255, 144/255, 218/255), (255/255, 169/255, 14/255), (189/255, 31/255, 1/255), (148/255, 164/255, 162/255), \
    (131/255, 45/255, 182/255), (169/255, 107/255, 89/255), (231/255, 99/255, 0/255), (185/255, 172/255, 112/255), \
    (113/255, 117/255, 129/255), (146/255, 218/255, 221/255)]

    h_mc, s_mc, h_data = [], [], None
    for s in samples.keys():        
        f = uproot.open(hdir+'/output/'+s+'.root')
        h = f['h']
        if s not in ['data']:
            s_mc.append(s)
            h_mc.append(h)
        else: h_data = h

    fig, ax = plt.subplots(figsize=(2088/options.dpi, 1416/options.dpi), dpi=options.dpi)
    hep.histplot(h_mc, label=s_mc, stack=True, color=cols[0:len(h_mc)], histtype='fill')
    hep.histplot(h_data, label='Data', histtype='errorbar', color='black', markersize=15)
    hep.cms.lumitext(options.detector+', '+options.energy)
    handles, labels = ax.get_legend_handles_labels()    
    ax.legend(handles[::-1], labels[::-1])
    ct = datetime.datetime.now()
    plt.text(0.00, 1.02, ct, color='lightgrey', transform=ax.transAxes, size=16)
    ax.set_xlabel('Observable')
    ax.set_ylabel('Events')
    plt.savefig(hdir+'/hist.png')