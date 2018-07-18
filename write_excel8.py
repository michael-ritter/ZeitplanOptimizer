'''Read a solution in a csv file, 
create the corresponding excel timetables'''



import csv
import xlsxwriter as xl
import argparse
import os
import sys
sys.path.append(os.path.abspath("."))
import data_loader8 as data_loader

# tools

# convert into readable name
def readable(fach):
    if "Hauptfach" in fach:
        res="Klassleiterfach"
    else:
        res=fach.split("_")[0]
    return res

class writer(object):

    def __init__(self,solution ="X.csv", source="source.xlsx", 
    destination="timetable.xlsx", log_message="writer_log.txt"):
        
        folder=os.path.abspath(".")
        if folder[-6:] == "python":
            folder = os.path.dirname(folder)
        
        self.X_path = os.path.join(folder,solution)
        self.source_path = os.path.join(folder,source)
        self.target_path = os.path.join(folder,destination)
        self.log_message = os.path.join(folder,log_message)
        
        self.import_data()
        self.create_timetables()
        self.create_timetables_lehrer()
        self.create_timetables_raume()
        #self.write_all()

    def import_data(self):
        #Import data
        self.reader = data_loader.reader(source=self.source_path)
        with open(self.X_path,"r") as f:
            self.X=list(csv.reader(f,delimiter=","))
        self.X=[[i.strip() for i in j] for j in self.X]
        
        
        #Parameters
        self.weekname=["Montag","Dienstag","Mittwoch","Donnerstag","Freitag","Samstag","Sonntag"]
        self.times=["8:00 - 8:45", "8:45 - 9:30", "9:50 - 10:35", "10:35 - 11:20", "11:35 - 12:20", "12:20 - 13:05", "13:05 - 14:00", "14:00 - 14:45", "14:45 - 15:30"]
        self.colours=["#F2A7A7","#F2A7D0","#E3A7F2","#CDA7F2",
                    "#ACA7F2","#A7BFF2","#A7D7F2","#A7EDF2","#A7F2D4","#A7F2A8","#D4F2A7",
                    "#F1F2A7","#F2DEA7",'#DEDCDB','#C4C2C2','#CCAA8D']


            
        # transform data in usable format
        self.header = self.X[0]
        self.content = [(*i[:3],int(i[3]),int(i[4])) for i in self.X[1:] if i[4]=="1"]

        self.courses = sorted(list(set([i[0] for i in self.content])))
        self.classes = sorted(list(set([i[1] for i in self.content])))
        self.lehrer = sorted(list(set([i[2] for i in self.content])))
        self.duration = {self.reader.fach_list[i] : self.reader.dauer[i] 
                for i in range(self.reader.n_fach)}
                
    def get_day(self,h):
        '''get day and time from hour number
        
        Args:
            h: int, hour number
            c: string, class name'''
        day=0 
        for i in self.reader.woche:
            if h<=i:
                return day,h-1
            else:
                h=h-i
                day+=1
        raise(RuntimeError("given h is not valid"))  
 
    def get_raum(self,fach):
        for raum,fach_list in enumerate(self.reader.raum_faecher):
            if fach in fach_list:
                return raum
        return None
 
    def create_timetables(self):
        """create timetable dict (more readable format)"""
        timetables = {i: {j: [[] for k in range(self.reader.woche[j])] 
                          for j in range(len(self.reader.woche))} for i in self.classes}
              
        for i in self.content:
            day,h=self.get_day(i[3])
            timetables[i[1]][day][h].append((i[0],i[2]))
            for s in range(self.duration[i[0]]-1):
                if h+s+1>=self.reader.woche[day]:
                    print("Warning: course %s is starting at %d but has duration %d"
                            %(i[0],h+1,self.duration[i[0]]))
                else:
                    timetables[i[1]][day][h+s+1].append((i[0],i[2]))
        self.timetables=timetables
    
    def create_timetables_lehrer(self):
        timetables = {i: {j: [[] for k in range(self.reader.woche[j])] 
                          for j in range(len(self.reader.woche))} for i in self.lehrer}
        
        for i in self.content:
            day,h=self.get_day(i[3])
            timetables[i[2]][day][h].append((i[0],i[1]))
            for s in range(self.duration[i[0]]-1):
                if h+s+1>=self.reader.woche[day]:
                    print("Warning: course %s is starting at %d but has duration %d"
                            %(i[0],h+1,self.duration[i[0]]))
                else:
                    timetables[i[2]][day][h+s+1].append((i[0],i[1]))
        self.timetables_lehrer=timetables
        
    def create_timetables_raume(self):
        raum_faecher=self.reader.raum_faecher
        nraum = len(raum_faecher)
        timetables = {i: {j: [[] for k in range(self.reader.woche[j])] 
                          for j in range(len(self.reader.woche))} for i in range(nraum)}
        
        for i in self.content:
            raum = self.get_raum(i[0])
            if raum is None:
                continue
            day,h = self.get_day(i[3])
            timetables[raum][day][h].append((i[0],i[1]))
            for s in range(self.duration[i[0]]-1):
                if h+s+1>=self.reader.woche[day]:
                    print("Warning: course %s is starting at %d but has duration %d"
                            %(i[0],h+1,self.duration[i[0]]))
                else:
                    timetables[raum][day][h+s+1].append((i[0],i[1]))
        self.timetables_raume={}
        for i in range(nraum):
            self.timetables_raume["raum%d"%(i+1)]=timetables[i]
    
    def coeff(self,f):
        read=self.reader
        f = read.fach_dict[f]
        dauer = read.dauer[f]
        geteilt = read.geteilt[f]
        return dauer/geteilt
        
    # Main functions
    def log_errors(self):
        message=[]
        temp = [[len([i for i in self.X if i[0]==f and i[1]==k])*self.coeff(f) 
            for f in self.reader.fach_list] for k in self.reader.klassen_list]
        for i,k in enumerate(self.reader.klassen_list):
            for j,f in enumerate(self.reader.fach_list):
                fehl = self.reader.stunden[i][j] - temp[i][j]
                if fehl>0:
                    message.append("Klasse {:10}: es fehlen {:2.0f} stunden für Fach '{:s}'".format(k,fehl,f))
            
            for gg in self.reader.gleichgultig[i]:
                fehl = gg[1]
                f1,f2=fehl,0
                for f in gg[0]:
                    j=self.reader.fach_dict[f]
                    f2+=self.reader.stunden[i][j]
                    fehl+=self.reader.stunden[i][j] - temp[i][j]
                if fehl>0:
                    message.append("Klasse {:10}: es fehlen {:2.0f} stunden für gleichgültige Fächer {:s} ".format(k,fehl,"%r"%(gg[0])))
        with open(self.log_message,"w") as f:
            f.write("\n".join(message))
        self.message=message
    
    def write_timetable(self,tt=None, destination=None):
        '''Create and saves an excel workbook with the timetables
        
        Args:
            tt: timetables dictionary (readable format)
            saveto: path to save the excel document
            
        Return:
            saveto
        '''
        if tt is None:
            tt=self.timetables
        if destination is None:
            destination=self.target_path

        wb=xl.Workbook(destination)
        courses,colours=self.courses,self.colours
        
        # defining cell formats
        format1={}
        format2={}
        format_dict={}
        i=0
        zeit_format=wb.add_format({"valign": "vcenter", "align": "center", "border": 2})
        for c in courses:
            if c=="Mittagspause":
                color="white"
            else:
                color=colours[i]
            format1[c]=wb.add_format({"align": "center",
                                      "bg_color":color})                          
            format2[c]=wb.add_format({"align": "center",
                                      "italic": True, "bg_color":colours[i]})
            format_dict[c]={"align": "center","bg_color":color}
            
            i=(i+1)%len(colours)
            
        bold = wb.add_format({'bold': True, "align": "center", "border": 2})
        italic = wb.add_format({'italic': True, "align": "center"})
        
        
        sheetnames=[]
        for c in tt.keys():
            
            # for each class, create a worksheet
            name=c.replace("/","_")
            if name.lower() in sheetnames:
                for i in range(10): 
                    name2="%s__(%d)"%(name,i+2)
                    if name2.lower() not in sheetnames:
                        ws=wb.add_worksheet(name2)
                        sheetnames.append(name2.lower())
                        break
            else:
                ws=wb.add_worksheet(name)
                sheetnames.append(name.lower())
                
            ws.set_column(1,100,15)
            x0=2
            y0=3
            
            ws.write(y0, x0-1, "Zeit", zeit_format)
            
            for i,stunde in enumerate(self.times):
                ws.merge_range(y0+2*i+1,x0-1,y0+2*i+2,x0-1,stunde, zeit_format)
           
          
            for day in range(len(self.reader.woche)):
                # contains the data for the class and day
                temp=tt[c][day] 

                if len(temp)==0:
                    continue
                day_length=len([i for i in temp if len(i)>0])
                
                # Nb of columns for that day
                M=max([len(i) for i in temp])-1
                # Title
                if M>0:
                    ws.merge_range(y0,x0,y0,x0+M,self.weekname[day],bold)
                else:
                    ws.write(y0,x0,self.weekname[day],bold)
                
                # Write the first n-1 cells and then the last 
                # For the last, merge the remaining cell of the row
                y1=y0-1
                stunde=0
                for h in temp:
                    stunde+=1
                    y1+=2
                    if len(h)==0:
                        continue
                    x1=x0
                    first=True
                    for j in h[:-1]:
                        
                        format = wb.add_format(format_dict[j[0]])
                        format2 = wb.add_format(format_dict[j[0]])
                        format2.set_italic()
                        
                        if first:
                            format.set_left(2)
                            format2.set_left(2)
                            first=False
                            
                        if stunde in [2,4,6,7]:
                            format2.set_bottom(2)
                            
                        ws.write(y1,x1,readable(j[0]),format)
                        
                        if stunde==day_length:
                            format2.set_bottom(2)
                        ws.write(y1+1,x1,'('+j[1]+')',format2)
                        x1+=1
                    
                    #letzte Zelle
                    j=h[-1]
                    format = wb.add_format(format_dict[j[0]])
                    format2 = wb.add_format(format_dict[j[0]])
                    format.set_right(2)
                    format2.set_right(2)
                    format2.set_italic()
                    
                    if first:
                            format.set_left(2)
                            format2.set_left(2)
                            
                    if stunde in [2,4,6,7]:
                        format2.set_bottom(2)
                        
                    if x1==x0+M:
                        ws.write(y1,x1,readable(j[0]),format)
                        if stunde==day_length:
                            format2.set_bottom(2)
                        ws.write(y1+1,x1,'('+j[1]+')',format2)
                    else:
                        ws.merge_range(y1,x1,y1,x0+M,readable(j[0]),format)
                        if stunde==day_length:
                            format2.set_bottom(2)
                        ws.merge_range(y1+1,x1,y1+1,x0+M,'('+j[1]+')',format2)
                x0+=M+1
        # save notebook
        wb.close()
        return destination

    def write_all(self):
        self.write_timetable()
        dest=".".join(self.target_path.split(".")[:-1])+"_lehrer.xlsx"
        self.write_timetable(tt=self.timetables_lehrer,destination=dest)
        dest=".".join(self.target_path.split(".")[:-1])+"_raume.xlsx"
        self.write_timetable(tt=self.timetables_raume,destination=dest)
        self.log_errors()
                    
def main(write_files=True,solution="X_res.csv",
        source="school_data.xlsx",
        destination="timetable.xlsx",
		command=False):
    """Parse argument, create writer object, write output files (timetables) 
    and return writer object"""
        
    if command:
        parser = argparse.ArgumentParser(description='Get source and destination file')
        parser.add_argument("--sol", dest="solution", type=str, 
                            default=solution,
                            help='The solution file (csv format)')
        parser.add_argument("--source", dest="source", type=str, 
                            default=source,
                            help='The source data file (mosel .dat format)')
        parser.add_argument('--dest', dest='destination', type=str,
                            default=destination,
                            help='The destination file (excel)')
        args = parser.parse_args()
        
        solution=args.solution
        source=args.source
        destination=args.destination
        
        write_files=True
    
    r=writer(solution=solution,source=source,destination=destination)
    if write_files:
        r.write_all()
    return r
    
if __name__=="__main__":
    main(command=True)
