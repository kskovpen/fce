import os, sys, math
import vector

class event():
    def __init__(self, ev, i):
        self.w = ev["weight"][i]

class lepton():
    idx = -1
    def __init__(self, ev, i, idx, typ):
        self.idx = idx
        self.typ = typ

        if typ == 0:
            self.pt = ev["electron_pt"][i][idx]
            self.eta = ev["electron_eta"][i][idx]
            self.phi = ev["electron_phi"][i][idx]
            self.e = ev["electron_e"][i][idx]
        else:
            self.pt = ev["muon_pt"][i][idx]
            self.eta = ev["muon_eta"][i][idx]
            self.phi = ev["muon_phi"][i][idx]
            self.e = ev["muon_e"][i][idx]
            
        self.p4 = vector.obj(pt=self.pt, eta=self.eta, phi=self.phi, e=self.e)
        
class jet():
    idx = -1
    def __init__(self, ev, i, idx):
        self.idx = idx

        self.pt = ev["jet_pt"][i][idx]
        self.eta = ev["jet_eta"][i][idx]
        self.phi = ev["jet_phi"][i][idx]
        self.e = ev["jet_e"][i][idx]
        self.isbtag = ev["jet_isbtag"][i][idx]
        self.p4 = vector.obj(pt=self.pt, eta=self.eta, phi=self.phi, e=self.e)        
