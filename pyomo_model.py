import numpy as np
import re
import data_loader7 as dl
import write_excel6 as wr
from importlib import reload
import pyomo.environ as pe
from pyomo.opt import SolverStatus, TerminationCondition

import sys,os
import argparse

# path parameter
folder=os.path.abspath(".")
currentpath=folder

#parameters 
class param:
    pass
    
LehrerAnzahlStrafe=2
GrosseStrafe=100
KlassenLehrerGewicht=8
TandemLehrerGewicht=3
PartnerLehrerGewicht=1
WechselGewicht=4
SportGewicht=1
RelaxStunden=True

DataFile = "school_data.xlsx"
WorkingFile = "X_res.csv"
OutputFile = "timetable.xlsx"
LogFile= "model_log.txt"
max_runtime = 200
solver="cbc"

    
############################################
###                                      ###
###             MAIN MODEL               ###
###                                      ###
############################################

    
class model():    

    def __init__(self, par):
        self.par=par
        self.r = dl.reader(source=par.DataFile)
        self.build()
  
    ############################################
    ###             UTILITIES                ###
    ############################################

    def dauer(self,f):
        return self.r.dauer[self.r.fach_dict[f]]

    def timerange(self,f,z):
        return np.arange(max(0,z+1-self.dauer(f)),z+1)

    def getUbergreifend(self,f,k):
        for i in self.r.ubergreifend:
            if i[0]==f and k in i[2]:
                return float(len(i[2]))
        return 1.0

    def checkx(self,f,k,l,z,verbose=False):
        """Erstelle nur variablen, 
        bei denen es ueberhaupt moeglich ist, 
        dass sie den Wert 1 annehmen"""
        
        r=self.r
        timerange=self.timerange
        getUbergreifend=self.getUbergreifend
        
        # Klassen Zeiten
        if r.klassen_zeiten[k][z]==0:
            if verbose: print(1)
            return False
        # Beachte die dauer von Blockstunden
        for t in np.arange(z+1,min(r.n_zeitslots,z+self.dauer(f))):
            if r.klassen_zeiten[k][t]==0:
                if verbose: print(2)
                return False
            if t in r.klassen_tagende[k]:
                if verbose: print(3)
                return False
        # Kein Unterricht mehr nach Schulschluss
        if z+self.dauer(f)-1 >= r.n_zeitslots:
            if verbose: print(4)
            return False
        # Kein Unterricht, wenn der Lehrer nicht da ist
        if l in r.lehrer_verfugbar.keys():
            if not z+1 in r.lehrer_verfugbar[l]:
                if verbose: print(5)
                return False
        # Kein Unterricht, wenn der Raum nicht verfuegbar ist
        for raum in range(len(r.raum_faecher)):
            if f in r.raum_faecher[raum]:
                if r.raum_verfugbar[raum][z]<=0:
                    if verbose: print(6)
                    return False
        # Soll vermeiden, dass ein 2-stundiger Kurs ueber eine Pause schreitet
        if self.dauer(f)>1:
            for tag in range(5):
                for i in [0,2,4]:
                    if z==r.tag_anfang[tag]+i:
                        if verbose: print(7)
                        return False
        return True

    def makex(self):
    
        r=self.r
        timerange=self.timerange
        getUbergreifend=self.getUbergreifend
        
        res=[]
        for l in r.lehrer_list:
            for k in r.klassen_list:
                temp=r.lehrer_faecher[r.lehrer_dict[l]]
                temp = [f for f in temp if f 
                        in r.klassenfach[r.klassen_dict[k]]]
                for f in temp:                
                    for z in range(r.n_zeitslots):
                        if self.checkx(f,k,l,z):
                            res.append((f,k,l,z))
        return res


    ############################################
    ###     DEFINE MODEL, SOLVE, WRITE       ###
    ############################################

    def build(self):
     
        r=self.r
        par=self.par
        timerange=self.timerange
        getUbergreifend=self.getUbergreifend
        
        m = pe.ConcreteModel()
        m.fach = pe.Set(initialize = r.fach_list, ordered=True)
        m.klas = pe.Set(initialize = r.klassen_list, ordered=True)
        m.lehrer = pe.Set(initialize = r.lehrer_list, ordered=True)
        m.zeit = pe.Set(initialize = range(r.n_zeitslots), ordered=True)
        m.x_set = pe.Set(initialize = self.makex(), ordered=True)
        m.x = pe.Var(m.x_set, domain = pe.Binary)



        ############################################
        ###                                      ###
        ###             CONSTRAINTS              ###
        ###                                      ###
        ############################################



        stundenRelaxiert = par.RelaxStunden



        # Vorgaben
        m.vorgaben_set = pe.Set(initialize=r.vorgaben.keys(),ordered=True)
        m.vorgaben = pe.Constraint(m.vorgaben_set*m.zeit,name="vorgaben")
        for k,i in m.vorgaben_set:
            for z in r.vorgaben_zeiten[(k,i)]:
                z=z-1
                temp=[]
                for l in m.lehrer:
                    for f in r.vorgaben[k,i]:
                        for t in timerange(f,z):
                            if (f,k,l,t) in m.x_set:
                                temp.append((f,k,l,t))
                if len(temp)==0:
                    continue
                m.vorgaben[k,i,z] = sum( m.x[f,k,l,z] for f,k,l,z in temp) >= 1
                
        # Vorgaben mit lehrer
        m.vorgaben_set_ml = pe.Set(initialize=r.vorgaben_mit_lehrer.keys(), ordered=True)
        m.vorgaben_ml = pe.Constraint(m.vorgaben_set_ml*m.zeit)
        for k,l,i in m.vorgaben_set_ml:
            for z in r.vorgaben_ml_zeiten[(k,i)]:
                temp=[]
                for f in r.vorgaben[k,i]:
                    for t in timerange(f,z):
                        if (f,k,l,t) in m.x_set:
                            temp.append((f,k,l,t))
                if len(temp)==0:
                    continue

        # Nur ein Unterricht pro Stunde (außer fuer geteilte Faecher)

        m.maxunterricht=pe.Constraint(m.klas*m.zeit)
        for k,z in m.klas*m.zeit:
            temp=[]
            for f in m.fach:
                for l in m.lehrer:
                    for t in timerange(f,z):
                        if (f,k,l,t) in m.x_set and f !="Tandem":
                            temp.append((f,k,l,t))
            if len(temp)==0:
                continue
            m.maxunterricht[k,z]= sum( m.x[f,k,l,z] / r.geteilt[r.fach_dict[f]]
                                      for f,k,l,z in temp) <= 1

        # Gleichzeitige Faecher
        # Wenn faecher gleicheitig stattfinden, setze die Summen als gleich

        m.gleichzeitig_set = pe.Set(initialize = r.gleichzeitig, ordered=True)
        m.gleichzeitigCtr = pe.Constraint(m.gleichzeitig_set*m.klas*m.zeit)
        for f1,f2,k,z in m.gleichzeitig_set*m.klas*m.zeit:
            temp1=[(f1,k,l,z) for l in m.lehrer if (f1,k,l,z) in m.x_set]
            temp2=[(f2,k,l,z) for l in m.lehrer if (f2,k,l,z) in m.x_set]
            if len(temp2)==0 and len(temp1)==0:
                continue
            m.gleichzeitigCtr[f1,f2,k,z]= sum( m.x[f1,k,l,z] for f1,k,l,z in temp1) == sum( m.x[f2,k,l,z] for f2,k,l,z in temp2)

        # Gleichzeitige und geteilte Faecher

        temp=[(f,k,z) for f in r.gleichzeitig_geteilt 
                      for k in m.klas 
                      for z in m.zeit
                      if f in r.klassenfach[r.klassen_dict[k]]]
        m.ggf_set = pe.Set(initialize=temp, ordered=True)
        m.ggf = pe.Var(m.ggf_set,domain="Binary")
        m.ggfCtr = pe.Constraint(m.ggf_set)

        for f,k,z in m.ggf_set:
            temp=[(f,k,l,t) for l in lehrer if (f,k,l,t) in m.x_set]
            if len(temp)==0:
                continue
            m.ggfCtr[f,k,z] = sum( m.x[f,k,l,z] / r.geteilt[r.fach_dict[f]]
                                      for f,k,l,z in temp) == m.ggf[f,k,z] 
            
        # Klassenuebergreifende Faecher (2 in 1)

        temp= []
        for f,i,k in r.ubergreifend:
            if len(k)>=2:
                for j in range(len(k)-1):
                    temp.append((f,k[j],k[j+1]))
        m.kug = pe.Set(initialize=temp, ordered=True)
        m.ubergreifendCtr = pe.Constraint(m.kug*m.lehrer*m.zeit)
        for f,k1,k2,l,z in m.kug*m.lehrer*m.zeit:
            if (f,k1,l,z) in m.x_set:
                if (f,k2,l,z) in m.x_set:
                    m.ubergreifendCtr[f,k1,k2,l,z] = m.x[f,k1,l,z]==m.x[f,k2,l,z]
                else:
                    m.ubergreifendCtr[f,k1,k2,l,z] = m.x[f,k1,l,z]==0
            else: 
                if (f,k2,l,z) in m.x_set:
                    m.ubergreifendCtr[f,k1,k2,l,z] = m.x[f,k2,l,z]==0
                    
        # Ein lehrer kann nur einen Unterricht geben 
        # (außer fuer klassenuebergreifende Faecher)

        m.lehrerFrei = pe.Constraint(m.lehrer*m.zeit)

        tempUber=set([f for f,i,k in r.ubergreifend])

        for l,z in m.lehrer*m.zeit:
            temp=[]
            for f in r.lehrer_faecher[r.lehrer_dict[l]]:
                for k in m.klas:
                    for t in timerange(f,z):
                        if f not in tempUber:
                            temp.append((f,k,t))
            for f,i,k in r.ubergreifend:
                if len(k)>=0 and f in r.lehrer_faecher[r.lehrer_dict[l]]:
                    for t in timerange(f,z):
                        temp.append((f,k[0],t))
                        
            temp=[(f,k,t) for f,k,t in temp if (f,k,l,t) in m.x_set]
            if temp==[]:
                continue

            m.lehrerFrei[l,z]= sum(m.x[f,k,l,t] for f,k,t in temp)<=1


        # Jeder Klasse muss gewisse UnterrichtStunden machen
        if not stundenRelaxiert: 
            m.stundenCtr = pe.Constraint(m.fach*m.klas)
            for f,k in m.fach*m.klas:
                temp=[(f,k,l,z) for l in m.lehrer for z in m.zeit
                     if (f,k,l,z) in m.x_set]
                if len(temp)==0: continue

                m.stundenCtr[f,k]= sum(m.x[f,k,l,z]*float(self.dauer(f))/float(r.geteilt[r.fach_dict[f]]) 
                    for f,k,l,z in temp) >= r.stunden[r.klassen_dict[k]][r.fach_dict[f]]

            
        # gleichgultige Faecher mussen zusaetzliche Unterrichtstunden machen

        tempgg=[]
        for i,k in enumerate(r.klassen_list):
            for ff,d in r.gleichgultig[i]:
                tempgg.append((k,tuple(ff),d))
        m.gleichgultig_set=pe.Set(initialize=range(len(tempgg)), ordered=True)

        m.gleichgultigCtr = pe.Constraint(m.gleichgultig_set)
        for i,j in enumerate(tempgg):
            k,ff,d = j 
            temp=[(f,k,l,z) for f in ff
                 for l in m.lehrer
                 for z in m.zeit
                 if (f,k,l,z) in m.x_set]
            if len(temp) == 0: 
                continue
            m.gleichgultigCtr[i]= sum(m.x[f,k,l,z]
                *float(self.dauer(f))/float(r.geteilt[r.fach_dict[f]])  
                for f,k,l,z in temp) >= d + sum(r.stunden[r.klassen_dict[k]][r.fach_dict[f]] for f in ff)

            
        # Tandemlehrer wird gebraucht

        m.tandemCtr = pe.Constraint(m.klas,m.zeit)
        for k,z in m.klas*m.zeit:
            temp1,temp2=[],[]
            for l in m.lehrer:
                if ("Tandem",k,l,z) in m.x_set:
                    temp2.append(("Tandem",k,l,z))
                for f in m.fach:
                    for t in timerange(f,z):
                        if (f,k,l,t) in m.x_set:
                            temp1.append((f,k,l,t))

            if len(temp1)+len(temp2)==0:
                continue
            m.tandemCtr[k,z] = sum(m.x[f,k,l,t]*r.tandem[r.fach_dict[f]] 
                for f,k,l,t in temp1) == sum(m.x[f,k,l,z] for f,k,l,z in temp2)
            
        # Lehrer sollten nicht Ihren Arbeitzeit ueberschreiten

        m.maxArbeitCtr = pe.Constraint(m.lehrer)
        for l in m.lehrer:
            temp=[(f,k,l,z) for f,k,z in m.fach*m.klas*m.zeit 
                  if (f,k,l,z) in m.x_set]
            if temp==[]:
                continue
            m.maxArbeitCtr[l]= sum(m.x[f,k,l,z]*self.dauer(f)/getUbergreifend(f,k)
                for f,k,l,z in temp)<= r.arbeitzeit[r.lehrer_dict[l]]

        # Raum Verfuegbarkeit

        m.raume = pe.Set(initialize=range(len(r.raum_faecher)), ordered=True)
        m.raumCtr = pe.Constraint(m.raume*m.zeit)
        for raum,z in m.raume*m.zeit:
            if r.raum_verfugbar[raum][z] < 1:
                continue
            temp=[]
            for f in r.raum_faecher[raum]:
                for k,l in m.klas*m.lehrer:
                    for t in timerange(f,z):
                        if (f,k,l,t) in m.x_set:
                            temp.append((f,k,l,t))
            if len(temp)==0:
                continue
            m.raumCtr[raum,z]=sum(m.x[f,k,l,t]/getUbergreifend(f,k) for f,k,l,t in temp)         <=r.raum_verfugbar[raum][z]




        ############################################
        ###                                      ###
        ###           SOFT CONSTRAINTS           ###
        ###                                      ###
        ############################################




        # Relaxation: jeder Klasse muss gewisse UnterrichtStunden machen
        if stundenRelaxiert: 
            m.stundenRel = pe.Var(m.fach*m.klas,domain=pe.NonNegativeReals)
            m.stundenCtr = pe.Constraint(m.fach*m.klas)
            for f,k in m.fach*m.klas:
                temp=[(f,k,l,z) for l in m.lehrer for z in m.zeit
                     if (f,k,l,z) in m.x_set]
                if len(temp)==0: continue

                m.stundenCtr[f,k]= sum(m.x[f,k,l,z]*float(self.dauer(f))/float(r.geteilt[r.fach_dict[f]]) 
                    for f,k,l,z in temp) + m.stundenRel[f,k]>= r.stunden[r.klassen_dict[k]][r.fach_dict[f]]


        # Lehrer Wechsel Variable
        m.wrange = pe.Set(initialize=[i for i in m.zeit if not i+1 in r.tag_anfang], ordered=True)
        m.lw = pe.Var(m.klas*m.wrange, domain = pe.NonNegativeReals)
        m.lwCtr = pe.Constraint(m.klas*m.wrange*m.lehrer)
        for k,z,l in m.klas*m.wrange*m.lehrer:
            temp1=[(f,t) for f in m.fach for t in timerange(f,z) if (f,k,l,t) in m.x_set]
            temp2=[(f,t) for f in m.fach for t in timerange(f,z-1) if (f,k,l,t) in m.x_set]
            if len(temp1)+len(temp2)==0:
                continue
            m.lwCtr[k,z,l] = m.lw[k,z]>=           sum(m.x[f,k,l,t] for f,t in temp1) -         sum(m.x[f,k,l,t] for f,t in temp2)
            
        # Sport zusammen 

        m.sportZusammen = pe.Var(m.klas*m.zeit,domain=pe.Binary)
        m.sportZusammenCtr = pe.Constraint(m.klas*m.zeit)
        for k,z in m.klas*m.zeit:
            temp1 = [l for l in m.lehrer if ("SportW",k,l,z) in m.x_set]
            temp2 = [l for l in m.lehrer if ("SportM",k,l,z) in m.x_set]
            m.sportZusammenCtr[k,z] = m.sportZusammen[k,z] <=         (sum(m.x["SportW",k,l,z] for l in temp1) + 
                sum(m.x["SportM",k,l,z] for l in temp2))/2.0
            
        # Minimiere den Anzahl von Lehrer pro Klasse
        m.lehrerInKlasse = pe.Var(m.klas*m.lehrer, domain=pe.Binary)
        m.lehrerInKlasseCtr = pe.Constraint(m.klas*m.lehrer)

        for k,l in m.klas*m.lehrer:
            m.lehrerInKlasseCtr[k,l]= m.lehrerInKlasse[k,l]     >= sum(m.x[f,k,l,z] for f in r.lehrer_faecher[r.lehrer_dict[l]]
                  for z in m.zeit if (f,k,l,z) in m.x_set)/(r.arbeitzeit[r.lehrer_dict[l]]+1)

                  
        ############################################
        ###                                      ###
        ### OBJECTIVE FUNCTION AND MAXIMIZATION  ###
        ###                                      ###
        ############################################
            
            
        def objRule(m):
            res=0
            
            # Lehrer Wechsel Variable
            res += - par.WechselGewicht * sum(m.lw[k,z] for k,z in m.klas*m.wrange)
            # Sport zusammen 
            res +=  par.SportGewicht * sum(m.sportZusammen[k,z] for k,z in m.klas*m.zeit)
            # Minimiere den Anzahl von Lehrer pro Klasse
            res += par.LehrerAnzahlStrafe * sum(m.lehrerInKlasse[k,l] 
                                            for k,l in m.klas*m.lehrer)
            
            # Hauptehrer unterrichtet am meisten in seiner eigenen Klasse.
            res += par.KlassenLehrerGewicht * sum(m.x[f,k,l,z] for f,k,l,z in m.x_set 
                       if l==r.klassen_lehrer[k])
            # Tandemlehrer unterrichtet am meisten in seiner eigenen Klasse.
            res += par.TandemLehrerGewicht * sum(m.x[f,k,l,z] for f,k,l,z in m.x_set 
                       if l==r.klassen_tandem[k])
            # Partnerlehrer unterrichtet am meisten in seiner eigenen Klasse.
            res += par.PartnerLehrerGewicht * sum(m.x[f,k,l,z] for f,k,l,z in m.x_set 
                       if l in r.klassen_partner[k])
            
            if stundenRelaxiert:
                res -= par.GrosseStrafe * sum(m.stundenRel[f,k] for f,k in m.fach*m.klas)

            return -res

        m.obj = pe.Objective(rule=objRule)

        self.m = m
        
    def solve(self):
        par = self.par
        
        if par.solver == "cbc":
            opt = pe.SolverFactory('cbc')
            opt.options["seconds"] = par.max_runtime
            results = opt.solve(self.m, tee=True)
        else:
            opt = pe.SolverFactory('glpk')
            opt.options["tmlim"] = par.max_runtime
            results = opt.solve(self.m, tee=True)

    def write(self):
        m=self.m
        par = self.par
        
        # write csv result file
        with open(par.WorkingFile,"w") as f:
            f.write("Faecher,Klassen,Lehrer,Zeitslots,x\n")
            for i in m.x:
                if m.x[i].value!=0 and m.x[i].value is not None:
                    f.write("%s,%s,%s,%s,%.f\n"%(*i[:3],i[3]+1,m.x[i].value))

        # writing log:
        with open(par.LogFile,"w") as f:
            f.write("Fehlermeldung für den Solver\n\n")
            for i in m.stundenRel:
                v=m.stundenRel[i].value
                if v!=0:
                    s="Fur Klasse %s konnten %d Stunden in Fach %s nicht gelehrt werden\n"%(i[1],v,i[0])
                    f.write(s)
                    
        # calling writer to output excel files
        w=wr.writer(solution=Par.WorkingFile, source=par.DataFile)
        w.write_all()


    
# getting arguments for the source and destination file

def main(write_files=True,command=False, solve=False):

    """
    Get arguments, create a pyomo model with given parameters
    """
    
    # reading the command line arguments
    if command:
        parser = argparse.ArgumentParser(description='Get model parameters')
        
        parser.add_argument('--source ', dest='DataFile', type=str,
                default=DataFile ,
                help='Specify the source file (excel)')
        parser.add_argument('--wrkfile ', dest='WorkingFile', type=str,
                default=WorkingFile ,
                help='Specify the intermediary file (csv)')
        parser.add_argument('--dest ', dest='OutputFile', type=str,
                default=OutputFile ,
                help='Specify the output file (excel)')
        parser.add_argument('--logfile', dest='LogFile', type=str,
                default=LogFile,
                help='Specify the log file (txt)')
        parser.add_argument('--max_runtime', dest='max_runtime', type=int,
                default=max_runtime,
                help='The max_runtime parameter')
        parser.add_argument('--solver ', dest='solver', type=str,
                default="cbc" ,
                help='Specify the solver : "cbc" (default) or "glpk"')
        
        parser.add_argument('--LehrerAnzahlStrafe', dest='LehrerAnzahlStrafe', type=int,
                default=LehrerAnzahlStrafe,
                help='The LehrerAnzahlStrafe parameter')
        parser.add_argument('--GrosseStrafe', dest='GrosseStrafe', type=int,
                default=GrosseStrafe,
                help='The GrosseStrafe parameter')
        parser.add_argument('--KlassenLehrerGewicht', dest='KlassenLehrerGewicht', type=int,
                default=KlassenLehrerGewicht,
                help='The KlassenLehrerGewicht parameter')
        parser.add_argument('--TandemLehrerGewicht', dest='TandemLehrerGewicht', type=int,
                default=TandemLehrerGewicht,
                help='The TandemLehrerGewicht parameter')
        parser.add_argument('--PartnerLehrerGewicht', dest='PartnerLehrerGewicht', type=int,
                default=PartnerLehrerGewicht,
                help='The PartnerLehrerGewicht parameter')
        parser.add_argument('--WechselGewicht', dest='WechselGewicht', type=int,
                default=WechselGewicht,
                help='The WechselGewicht parameter')
        parser.add_argument('--SportGewicht', dest='SportGewicht', type=int,
                default=SportGewicht,
                help='The SportGewicht parameter')
                
        parser.add_argument('--RelaxStunden', dest='RelaxStunden', type=bool,
                default=RelaxStunden,
                help='Ob die Bedingung "UnterrichtStunden" relaxiert werden soll: '+
                "Wenn 'cbc' oder 'glpk' benutzt werden, sollte es 'True' sein")
        
        par = parser.parse_args()
        
        par.DataFile    = os.path.join(folder,par.DataFile )
        par.OutputFile  = os.path.join(folder,par.OutputFile) 
        par.LogFile     = os.path.join(folder,par.LogFile)
        par.WorkingFile = os.path.join(folder,par.WorkingFile)
        
    else:
        par = param()
        
        par.DataFile    = os.path.join(folder,DataFile )
        par.OutputFile  = os.path.join(folder,OutputFile) 
        par.LogFile     = os.path.join(folder,LogFile)
        par.WorkingFile = os.path.join(folder,WorkingFile)
        
        par.max_runtime = max_runtime
        par.solver      = solver
        
        par.LehrerAnzahlStrafe   = LehrerAnzahlStrafe
        par.GrosseStrafe         = GrosseStrafe
        par.KlassenLehrerGewicht = KlassenLehrerGewicht
        par.TandemLehrerGewicht  = TandemLehrerGewicht
        par.PartnerLehrerGewicht = PartnerLehrerGewicht
        par.WechselGewicht       = WechselGewicht
        par.SportGewicht         = SportGewicht
        par.RelaxStunden         = RelaxStunden
    
    mymodel=model(par)
    
    if solve:
        mymodel.solve()
        
    if write_files:
        mymodel.write()

    return True

if __name__=="__main__":
    main(command=True,solve=True)

# Remarks: 

#  - gleichgultig is empty
