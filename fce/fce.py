from PyQt6.QtCore import QDateTime, Qt, QTimer, QRect, QPoint, QFile, QIODevice, QPropertyAnimation, QEasingCurve, QLocale
from PyQt6.QtGui import QPixmap, QPainter, QColor, QIntValidator, QDoubleValidator, QTextOption, QTextLength, QBrush, QPalette, QTextCursor
from PyQt6.QtWidgets import (QApplication, QCheckBox, QComboBox, QDateTimeEdit, 
QDial, QDialog, QGridLayout, QGroupBox, QHBoxLayout, QLabel, QLineEdit, QFileDialog, QLayout,
QProgressBar, QPushButton, QRadioButton, QScrollBar, QSizePolicy, QGraphicsOpacityEffect, QListWidget,
QSlider, QSpinBox, QStyleFactory, QTableWidget, QTabWidget, QTextEdit, QVBoxLayout, QWidget)
import json, subprocess, threading, time, os, sys, py_compile, pkgutil, filecmp
from optparse import OptionParser

version = '0.0.1c'

os.environ['LC_ALL'] = 'en_US.UTF-8'
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'

_ROOT = os.path.abspath(os.path.dirname(__file__))
def fget(path):
    return os.path.join(_ROOT, '', path)

lock = threading.Lock()

home = os.path.expanduser('~')
hdir = home+'/.fce'
if not os.path.isdir(hdir):
    os.system('mkdir '+hdir)

settings = None
if os.path.isfile(hdir+'/settings.json'):
    fs = open(hdir+'/settings.json')
    settings = json.load(fs)
    
f = open(fget('config/samples.json'))
samples = json.load(f)

def updateAnalysis():
    
    log = ''
    
    with open(fget("rundefault.py"), "r") as in_file: buf = in_file.readlines()
    with open(fget("config/selection.dat"), "r") as in_file: selection = in_file.readlines()        
    with open(fget("config/analysis.dat"), "r") as in_file: analysis = in_file.readlines()
    with open(fget("config/skim.dat"), "r") as in_file: skim = in_file.readlines()
        
    hasSelection, hasObservable, hasSkim = False, False, False
    with open(hdir+"/run.py", "w") as out_file:
        for iline, line in enumerate(buf):
            if 'selectionkey' in line:
                selectioncode = ''
                for lsel in selection: selectioncode += '                '+lsel+'\n'
                line = selectioncode + line
            if 'observablekey' in line:
                analysiscode = ''
                for lana in analysis: analysiscode += '                '+lana+'\n'
                line = analysiscode + line
            if 'skimkey' in line:
                skimcode = ''
                for lski in skim: skimcode += '                '+lski+'\n'
                line = skimcode + line
            out_file.write(line)
    with open(hdir+"/run.py", "r") as in_file:
        buf = in_file.readlines()
        for line in buf:
            if (not hasSelection) and 'passevent' in line and not 'selectionkey' in line:
                hasSelection = True
            if (not hasObservable) and 'observable' in line and not 'observablekey' in line:
                hasObservable = True
            if (not hasSkim) and 'skim' in line and not 'skimkey' in line:
                hasSkim = True

    try: 
        py_compile.compile(hdir+'/run.py', doraise=True)
    except py_compile.PyCompileError as e:
        log = e.exc_value
        
    if not hasSelection: log = 'Can not find passevent!\n'
    if not hasObservable: log += 'Can not find observable!\n'
    if not hasSkim: log += 'Can not find skim!\n'
    
    return log

class RunMonitor(threading.Thread):
    
    def __init__(self, runModule, gallery):
        
        threading.Thread.__init__(self)
        self.runModule = runModule
        self.settingsWindow = gallery.settingsWindow
        self.controlWindow = gallery.controlWindow
        self.resultWindow = gallery.resultWindow
        self.exitWindow = gallery.exitWindow
        self.bestFit = gallery.bestFit
        self.significanceObserved = gallery.significanceObserved
        self.significanceExpected = gallery.significanceExpected
        
    def run(self):
        
        while True:
            time.sleep(0.5)

            data = self.settingsWindow.findChildren(QComboBox)
            for d in data:
                name = d.objectName()
                if name == 'Energy':
                    if self.runModule.energy != d.itemText(d.currentIndex()):
                        self.runModule.energy = d.itemText(d.currentIndex())
                        det = self.settingsWindow.findChildren(QComboBox)
                        for dd in det:
                            name = dd.objectName()
                            if name == 'Target':
                                dd.clear()
                                for s in samples[self.runModule.energy.replace(' GeV', '')].keys():
                                    if s == 'data': continue
                                    dd.addItem(s)
                                dd.addItem('New physics')
                                dd.addItem('None')
                                dd.setCurrentIndex(dd.findText(dd.itemText(dd.count()-1)))
                                self.runModule.target = dd.itemText(dd.count()-1)

            if hasattr(self.runModule, 'process'):
                self.status = bool(self.runModule.process.poll() == 0)
                if self.status:
                    self.runModule.done = True
                    pb = self.exitWindow.findChildren(QProgressBar)[0]
                    pb.hide()
                    
                    buttons = self.controlWindow.findChildren(QPushButton)
                    for b in buttons:
                        if b.objectName() == 'RunButton':
                            result = self.resultWindow.findChildren(QLabel)
                            img = QPixmap(hdir+'/hist.png')
                            img.setDevicePixelRatio(4)
                            result[0].setPixmap(img)
                            b.setText('Run')

                    if os.path.isfile(hdir+'/result.json') and self.runModule.target != 'None' and not self.runModule.shown:
                        ffit = open(hdir+'/result.json')
                        fitresult = json.load(ffit)
                            
                        results = self.resultWindow.findChildren(QLabel)
                        for r in results:
                            if r.objectName() == 'BestFit':
                                if fitresult['bestfit']:
                                    bestfit = "{:.3f}".format(fitresult['bestfit'])
                                    uncertainty = "{:.3f}".format(fitresult['uncertainty'])
                                    r.setText(self.bestFit+'      '+bestfit+'\n      +/- '+uncertainty)
                                else:
                                    r.setText(self.bestFit)
                            elif r.objectName() == 'SignificanceObserved':
                                significanceobserved = "{:.3f}".format(fitresult['observed_significance'])
                                r.setText(self.significanceObserved+'      '+significanceobserved)
                            elif r.objectName() == 'SignificanceExpected':
                                if fitresult['expected_significance']:                                    
                                    significanceexpected = "{:.3f}".format(fitresult['expected_significance'])
                                else:
                                    significanceexpected = ""
                                r.setText(self.significanceExpected+'      '+significanceexpected)
                        self.runModule.shown = True
                    elif not self.runModule.shown:
                        results = self.resultWindow.findChildren(QLabel)
                        for r in results:
                            if r.objectName() == 'BestFit':
                                r.setText(self.bestFit)
                            elif r.objectName() == 'SignificanceObserved':
                                r.setText(self.significanceObserved)
                            elif r.objectName() == 'SignificanceExpected':
                                r.setText(self.significanceExpected)
                        self.runModule.shown = True
            
class RunModule(threading.Thread):
    def __init__(self, evt, dpi):
        super(RunModule, self).__init__()
        self.stdout = None
        self.stderr = None
        self.evt = evt
        self.dpi = dpi
        self.doskim = False
        self.useskim = False
        self.bins = '5' if not settings else settings['Bins']
        self.min = '0.0' if not settings else settings['Min']
        self.max = '5.0' if not settings else settings['Max']
        self.energy = '91 GeV' if not settings else settings['Energy']
        self.detector = 'IDEA' if not settings else settings['Detector']
        self.target = 'None' if not settings else settings['Target']
        self.data = '' if not settings else settings['Data']
        self.done = False
        self.shown = False
    def run(self):
        self.shown = False
        if os.path.isdir(hdir+'/skim'): self.useskim = True
        else: self.useskim = False
        if self.doskim: self.useskim = False
        if not self.done:
            self.doskim = True
            self.useskim = False
        print('exec python3 '+hdir+'/run.py --bins='+str(self.bins)+' --min='+str(self.min)+' --max='+str(self.max)+\
        ' --energy=\"'+str(self.energy)+'\" --detector=\"'+str(self.detector)+'\" --target=\"'+str(self.target)+\
        '\" --data=\"'+str(self.data)+'\" --dpi=\"'+str(self.dpi)+'\"'+(' --doskim' if self.doskim else '')+(' --useskim' if self.useskim else ''))
#        print('useskim=', self.useskim, 'doskim=', self.doskim)
        cmd = ['exec python3 '+hdir+'/run.py --bins='+str(self.bins)+' --min='+str(self.min)+' --max='+str(self.max)+\
        ' --energy=\"'+str(self.energy)+'\" --detector=\"'+str(self.detector)+'\" --target=\"'+str(self.target)+\
        '\" --data=\"'+str(self.data)+'\" --dpi=\"'+str(self.dpi)+'\"'+(' --doskim' if self.doskim else '')+(' --useskim' if self.useskim else '')]
        self.process = subprocess.Popen(
          cmd,
          stdout=subprocess.PIPE,
          stderr=subprocess.PIPE,
          shell=True
        )
        self.done = False
    def stop(self):
        if hasattr(self, 'process'):
            self.evt.set()
            self.process.kill()

class WidgetGallery(QDialog):
    
    def __init__(self, runModule, app, parent=None):
        
        super(WidgetGallery, self).__init__(parent)
      
        self.app = app
        self.runModule = runModule
        
        self.createBasicWindow()
        self.createSettingsWindow()
        self.createResultWindow()
        self.createCodeWindow()
        self.createControlWindow()
        self.createExitWindow()
                        
        self.mainLayout = QGridLayout(self)
        self.mainLayout.addWidget(self.basicWindow, 0, 0)
        self.mainLayout.addWidget(self.settingsWindow, 0, 1)
        self.mainLayout.addWidget(self.resultWindow, 1, 1)
        self.mainLayout.addWidget(self.codeWindow, 1, 0)
        self.mainLayout.addWidget(self.controlWindow, 2, 0)
        self.mainLayout.addWidget(self.exitWindow, 2, 1)
        self.setLayout(self.mainLayout)
        self.setWindowTitle("Future Collider Experiment")
        
        self.setWindowFlags(Qt.WindowType.CustomizeWindowHint | Qt.WindowType.WindowTitleHint | Qt.WindowType.WindowMinimizeButtonHint)
        self.mainLayout.setSizeConstraint(QLayout.SizeConstraint.SetFixedSize)
        
    def createResultWindow(self):

        self.resultWindow = QWidget()
        self.bestFit = 'Best fit:\n\n'
        self.significanceObserved = 'Significance\n (observed):\n\n'
        self.significanceExpected = 'Significance\n (expected):\n\n'
        
        label = QLabel()
        if os.path.isfile(hdir+'/hist.png'): result = QPixmap(hdir+'/hist.png')
        else:
            result = QPixmap(2088, 1416)
            clrbg = QColor(255, 255, 255)
            result.fill(clrbg);
        result.setDevicePixelRatio(4)
        label.setPixmap(result)

        labelFit = QLabel()
        labelFit.setText(self.bestFit)
        labelFit.setObjectName('BestFit')
        labelSignificanceObserved = QLabel()
        labelSignificanceObserved.setText(self.significanceObserved)
        labelSignificanceObserved.setObjectName('SignificanceObserved')
        labelSignificanceExpected = QLabel()
        labelSignificanceExpected.setText(self.significanceExpected)
        labelSignificanceExpected.setObjectName('SignificanceExpected')
        
        tab2hbox = QGridLayout()
        tab2hbox.addWidget(label, 0, 0, 0, 1)
        tab2hbox.addWidget(labelFit, 0, 1, alignment=Qt.AlignmentFlag.AlignTop)
        tab2hbox.addWidget(labelSignificanceObserved, 1, 1, alignment=Qt.AlignmentFlag.AlignTop)
        tab2hbox.addWidget(labelSignificanceExpected, 2, 1, alignment=Qt.AlignmentFlag.AlignTop)
        self.resultWindow.setLayout(tab2hbox)
        
    def createCodeWindow(self):
        
        self.codeWindow = QWidget()

        codeSkim = QTextEdit()
        codeSkim.setObjectName('Skim')
        codeSkim.setFixedWidth(261)
        codeSkim.setFixedHeight(60)
        f = QFile(fget('config/skim.dat'))
        f.open(QIODevice.OpenModeFlag.ReadOnly | QIODevice.OpenModeFlag.Text)
        content = str(f.readAll(), 'utf-8')
        codeSkim.setPlainText(content)
        
        codeSelection = QTextEdit()
        codeSelection.setObjectName('Selection')
        codeSelection.setFixedWidth(261)
        codeSelection.setFixedHeight(140)
        f = QFile(fget('config/selection.dat'))
        f.open(QIODevice.OpenModeFlag.ReadOnly | QIODevice.OpenModeFlag.Text)
        content = str(f.readAll(), 'utf-8')
        codeSelection.setPlainText(content)

        codeAnalysis = QTextEdit()
        codeAnalysis.setObjectName('Analysis')
        codeAnalysis.setFixedWidth(261)
        codeAnalysis.setFixedHeight(140)
        f = QFile(fget('config/analysis.dat'))
        f.open(QIODevice.OpenModeFlag.ReadOnly | QIODevice.OpenModeFlag.Text)
        content = str(f.readAll(), 'utf-8')
        codeAnalysis.setPlainText(content)
        
        codeLayout = QVBoxLayout()
        codeLayout.setContentsMargins(5, 5, 5, 5)
        codeLayout.addWidget(codeSkim)
        codeLayout.addWidget(codeSelection)
        codeLayout.addWidget(codeAnalysis)
        self.codeWindow.setLayout(codeLayout)

    def createControlWindow(self):
        
        self.controlWindow = QWidget()

        self.runButton = QPushButton("Run")
        self.runButton.setObjectName("RunButton")
        self.runButton.clicked.connect(self.runAnalysis)

        layout = QVBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)
        layout.addWidget(self.runButton)
        layout.addStretch(2)
        self.controlWindow.setLayout(layout)

    def getCurrentSettings(self):
        
        labels = self.settingsWindow.findChildren(QLabel)
        for l in labels:
            if l.objectName() == 'SetOK':
                l.show()
                eff = QGraphicsOpacityEffect()
                l.setGraphicsEffect(eff)
                anim = QPropertyAnimation(l, propertyName=b"opacity", targetObject=eff, duration=500, startValue=1.0, endValue=0.0)
                anim.start()
                anim.finished.connect(l.hide)
                break
        
        fields = self.settingsWindow.findChildren(QLineEdit)
        fields += self.settingsWindow.findChildren(QComboBox)
        for f in fields:
            name = f.objectName()
            if name == 'Bins': self.runModule.bins = f.text()
            elif name == 'Min': self.runModule.min = f.text()
            elif name == 'Max': self.runModule.max = f.text()
            elif name == 'Energy': self.runModule.energy = f.itemText(f.currentIndex())
            elif name == 'Detector': self.runModule.detector = f.itemText(f.currentIndex())
            elif name == 'Target': self.runModule.target = f.itemText(f.currentIndex())
            elif name == 'Data': self.runModule.data = f.text()
            
        os.system('rm -rf '+hdir+'/settings.json')
        settings = {'Bins': self.runModule.bins, 'Min': self.runModule.min, 'Max': self.runModule.max, \
        'Energy': self.runModule.energy, 'Detector': self.runModule.detector, 'Target': self.runModule.target, \
        'Data': self.runModule.data}
        json_data = json.dumps(settings, indent=4)
        with open(hdir+'/settings.json', 'w') as outfile:
            outfile.write(json_data)

    def exitApplication(self):

        self.runModule.stop()
        self.close()
        os._exit(1)
        
    def createExitWindow(self):
        
        self.exitWindow = QWidget()

        self.pb = QProgressBar()
        self.pb.setFixedWidth(200)
        self.pb.setMinimum(0)
        self.pb.setMaximum(0)
        self.pb.setValue(0)
        self.pb.hide()
        
        self.exitButton = QPushButton("Exit")
        self.exitButton.clicked.connect(self.exitApplication)

        layout = QHBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)
        layout.addWidget(self.pb, 1000, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.exitButton, 1, alignment=Qt.AlignmentFlag.AlignRight)
        self.exitWindow.setLayout(layout)

    def showAbout(self):
        
        def createPopupAbout():
            
            self.wabout = QWidget()
            self.wabout.setGeometry(QRect(150, 100, 150, 100))
            glopos = self.mapToGlobal(self.rect().center())
            self.wabout.move(int(glopos.x() - self.wabout.width() / 2), int(glopos.y() - self.wabout.height() / 2))
            layout = QVBoxLayout()
            layout.setContentsMargins(5, 5, 5, 5)
            inq = QLabel()
            inq.setText("Future Collider Experiment")
            ver = QLabel()
            ver.setText("v"+version)
            contact = QLabel()
            contact.setText('<a href=\"mailto:kirill.skovpen@ugent.be\">kirill.skovpen@ugent.be</a>')
            contact.setOpenExternalLinks(True)
            exitButton = QPushButton("Close")
            exitButton.clicked.connect(self.wabout.close)
            layout.addWidget(inq, alignment=Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(ver, alignment=Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(contact, alignment=Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(exitButton)
            self.wabout.setLayout(layout)
            
        createPopupAbout()
        self.wabout.show()

    def showHelp(self):
        
        def createPopupHelp():
            
            self.whelp = QWidget()
            self.whelp.setGeometry(QRect(400, 250, 400, 250))
            glopos = self.mapToGlobal(self.rect().center())
            self.whelp.move(int(glopos.x() - self.whelp.width() / 2), int(glopos.y() - self.whelp.height() / 2))
            layout = QVBoxLayout()
            layout.setContentsMargins(5, 5, 5, 5)
            desc = QTextEdit()
            desc.setFixedWidth(550)
            c = self.whelp.palette().color(self.whelp.backgroundRole()).name()
            variables = {'Event variables': 'Description', 
            'nelectrons': 'Number of electrons', 'nmuons': 'Number of muons', 'nphotons': 'Number of photons', 'njets': 'Number of jets',
            'electrons[nelectrons]': 'Collection of electrons', 'muons[nmuons]': 'Collection of muons', 'photons[nphotons]': 'Collection of photons',
            'jets[njets]': 'Collection of jets',
            '': '', 'Object variables': 'Description',
            '.p4': 'Four-momentum', '.pt': 'Transverse momentum', '.eta': 'Pseudorapidity', '.phi': 'Azimuthal angle', '.e': 'Energy',
            '.d0': 'Transverse impact parameter (leptons only)',
            '.z0': 'Longitudinal impact parameter (leptons only)',
            '.d0signif': 'Transverse impact parameter significance (leptons only)',
            '.z0signif': 'Longitudinal impact parameter significance (leptons only)',
            '.btag': 'Heavy-flavour tagging score (jets only)',
            ' ': ' ', 'Output variables':  'Description',
            'skim': 'Boolean flag for skimmed events',
            'passevent': 'Boolean flag for selected events', 'observable': 'Variable to plot'}
            desc.setStyleSheet("background-color: "+c+"; border: 0px")
            desc.setReadOnly(True)
            desc.setWordWrapMode(QTextOption.WrapMode.WrapAnywhere)
            desc.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
            tab = desc.textCursor().insertTable(len(variables.keys()), 2)
            for ik in range(len(variables.keys())):
                k = list(variables.keys())[ik]
                tab.cellAt(ik, 0).firstCursorPosition().insertText(k)
                tab.cellAt(ik, 1).firstCursorPosition().insertText(variables[k])
            fmt = tab.format()
            fmt.setCellSpacing(0)
            fmt.setBorderBrush(QBrush(Qt.BrushStyle.SolidPattern))
            fmt.setWidth(QTextLength(QTextLength.Type.PercentageLength, 100))
            tab.setFormat(fmt)
            desc.moveCursor(QTextCursor.MoveOperation.Start)
            exitButton = QPushButton("Close")
            exitButton.clicked.connect(self.whelp.close)
            exitButton.setFixedWidth(100)
            layout.addWidget(desc, alignment=Qt.AlignmentFlag.AlignCenter, stretch=90)
            layout.addWidget(exitButton, alignment=Qt.AlignmentFlag.AlignCenter, stretch=10)
            self.whelp.setLayout(layout)
            
        createPopupHelp()
        self.whelp.show()
        
    def runAnalysis(self):
        
        def confirm():
            
            self.runModule.stop()
            pb = self.exitWindow.findChildren(QProgressBar)[0]
            pb.hide()
            img = QPixmap(hdir+"/hist.png")
            img.setDevicePixelRatio(4)
            result = self.resultWindow.findChildren(QLabel)
            result[0].setPixmap(img)
            self.runButton.setText("Run")
            self.wstop.close()

        def createPopupStop():
            
            self.wstop = QWidget()
            self.wstop.setGeometry(QRect(150, 100, 150, 100))
            glopos = self.mapToGlobal(self.rect().center())
            self.wstop.move(int(glopos.x() - self.wstop.width() / 2), int(glopos.y() - self.wstop.height() / 2))
            layout = QGridLayout()
            layout.setContentsMargins(5, 5, 5, 5)
            inq = QLabel()
            inq.setText("Are you sure?")
            confirmButton = QPushButton("Yes")
            confirmButton.clicked.connect(confirm)
            exitButton = QPushButton("No")
            exitButton.clicked.connect(self.wstop.close)
            layout.addWidget(inq, 0, 0, 1, 0, alignment=Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(confirmButton, 1, 0)
            layout.addWidget(exitButton, 1, 1)
            self.wstop.setLayout(layout)

        def createPopupParse(log = ''):
            
            self.wparse = QWidget()
            self.wparse.setGeometry(QRect(150, 100, 150, 100))
            glopos = self.mapToGlobal(self.rect().center())
            self.wparse.move(int(glopos.x() - self.wparse.width() / 2), int(glopos.y() - self.wparse.height() / 2))
            layout = QGridLayout()
            layout.setContentsMargins(5, 5, 5, 5)
            inq = QLabel()
            inq.setFixedWidth(300)
            inq.setWordWrap(True)
            inq.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
            inq.setText("Syntax error:\n"+str(log))
            exitButton = QPushButton("OK")
            exitButton.clicked.connect(self.wparse.close)
            layout.addWidget(inq, 0, 0, 1, 0, alignment=Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(exitButton, 1, 1, alignment=Qt.AlignmentFlag.AlignCenter)
            self.wparse.setLayout(layout)

        def createPopupData():
            
            self.wdata = QWidget()
            self.wdata.setGeometry(QRect(150, 100, 150, 100))
            glopos = self.mapToGlobal(self.rect().center())
            self.wdata.move(int(glopos.x() - self.wdata.width() / 2), int(glopos.y() - self.wdata.height() / 2))
            layout = QVBoxLayout()
            layout.setContentsMargins(5, 5, 5, 5)
            inq = QLabel()
            inq.setFixedWidth(300)
            inq.setWordWrap(True)
            inq.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
            inq.setText("Data directory not found!")
            exitButton = QPushButton("OK")
            exitButton.clicked.connect(self.wdata.close)
            layout.addWidget(inq, alignment=Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(exitButton, alignment=Qt.AlignmentFlag.AlignCenter)
            self.wdata.setLayout(layout)
            
        createPopupStop()

        pb = self.exitWindow.findChildren(QProgressBar)[0]
        
        if self.runButton.text() == "Run":
#            self.getCurrentSettings()
#            if not hasattr(self.runModule, 'process'): self.runModule.start()
#            else: self.runModule.run()
            if self.runModule.data == '' or not os.path.isdir(self.runModule.data) \
            or not os.path.isdir(self.runModule.data+self.runModule.detector) \
            or not os.path.isdir(self.runModule.data+self.runModule.detector+'/'+self.runModule.energy.replace(' ', '')):
                createPopupData()
                self.wdata.show()
            else:
                code = self.codeWindow.findChildren(QTextEdit)
                for c in code:
                    for l in ['selection', 'analysis', 'skim']:                        
                        if c.objectName() == l.capitalize():
                            d = c.toPlainText()
                            with open(fget('config/'+l+".dat"), "w") as out_file:
                                out_file.write(d)
                            if c.objectName() == 'Skim':
                                if not os.path.isfile(fget('config/'+l+'_old.dat')) or not os.path.isdir(hdir+'/skim'):
                                    self.runModule.doskim = True
                                else:
                                    fcr = filecmp.cmp(fget('config/'+l+'.dat'), fget('config/'+l+'_old.dat'), shallow=False)
                                    if not fcr: self.runModule.doskim = True
                                    else: self.runModule.doskim = False
                                os.system('cp '+fget('config/'+l+'.dat')+' '+fget('config/'+l+'_old.dat'))
                log = updateAnalysis()
                if log:
                    createPopupParse(log)
                    self.wparse.show()
                else:
                    w = self.resultWindow.findChildren(QLabel)
                    if len(w) > 0:
                        p = w[0].pixmap()
                        if not p.isNull():
                            npix = QPixmap(p.size())
                            npix.setDevicePixelRatio(4)
                            npix.fill(QColor(0,0,0,0))
                            painter = QPainter(npix)
                            painter.setOpacity(0.2)
                            painter.drawPixmap(QPoint(), p)
                            painter.end()
                            w[0].setPixmap(npix)            
                    self.runButton.setText("Stop")
                    pb.show()
            if not hasattr(self.runModule, 'process'): self.runModule.start()
            else: self.runModule.run()
        else:
            lock.acquire()
            if self.runModule.process.poll() != 0:
                self.wstop.show()
            lock.release()
            if self.runModule.process.poll() == 0:                
                self.runModule.stop()
                self.runButton.setText("Run")
        
    def createBasicWindow(self):
        
        self.basicWindow = QWidget()
        
        aboutButton = QPushButton("About")
        helpButton = QPushButton("Help")

        aboutButton.clicked.connect(self.showAbout)
        helpButton.clicked.connect(self.showHelp)
        
        img = QPixmap(fget('data/fce.ico'))
        img.setDevicePixelRatio(8)
        logo = QLabel()
        logo.setPixmap(img)
        
        layout = QGridLayout()
        layout.setContentsMargins(5, 5, 5, 5)
        layout.addWidget(logo, 0, 0, 2, 1, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(aboutButton, 0, 1)
        layout.addWidget(helpButton, 1, 1)
        self.basicWindow.setLayout(layout)

    def createSettingsWindow(self):
        
        self.settingsWindow = QWidget()

        labelData = QLabel()
        labelData.setText("Data:")
                        
        class data(QLineEdit):
            def __init__(self, runModule):
                super().__init__()
                self.runModule = runModule
                self.setText(runModule.data)
            def mousePressEvent(self, e):
                dd = str(QFileDialog.getExistingDirectory(self, "Select Directory"))
                self.setText(dd+'/')
                self.runModule.data = dd+'/'
                
        dataSelection = data(self.runModule)
        dataSelection.setObjectName('Data')
        
        labelEnergy = QLabel()
        labelEnergy.setText("Energy:")
        
        energy = QComboBox()
        energy.addItem('91 GeV')
        energy.addItem('160 GeV')
        energy.addItem('240 GeV')
        energy.addItem('365 GeV')
        energy.setObjectName('Energy')
        energy.setCurrentIndex(energy.findText(self.runModule.energy))

        labelDetector = QLabel()
        labelDetector.setText("Detector:")
        
        detector = QComboBox()
        detector.addItem('IDEA')
        detector.addItem('CLD')
        detector.setObjectName('Detector')
        detector.setCurrentIndex(detector.findText(self.runModule.detector))

        labelTarget = QLabel()
        labelTarget.setText("Target:")
        
        target = QComboBox()
        for s in samples[self.runModule.energy.replace(' GeV', '')].keys():
            if s == 'data': continue
            target.addItem(s)
        target.addItem('New physics')
        target.addItem('None')
        target.setObjectName('Target')
        target.setCurrentIndex(target.findText(self.runModule.target))

        setButton = QPushButton("Set")
        setButton.clicked.connect(self.getCurrentSettings)

        setOK = QLabel()
        setOK.setObjectName("SetOK")
        setOK.setText("OK!")
        setOK.setAlignment(Qt.AlignmentFlag.AlignCenter| Qt.AlignmentFlag.AlignVCenter)
        setOK.hide()
        
        labelBins = QLabel()
        labelBins.setText("Bins:")
        labelBins.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        
        bins = QLineEdit()
        bins.setText(self.runModule.bins)
        bins.setValidator(QIntValidator(0, 300))
        bins.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        bins.setObjectName('Bins')

        labelMin = QLabel()
        labelMin.setText("Min:")
        labelMin.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        val = QDoubleValidator()
        val.setNotation(QDoubleValidator.Notation.StandardNotation)
        val.setLocale(QLocale("en_US"))
        val.setDecimals(5)
        
        min = QLineEdit()
        min.setText(self.runModule.min)
        min.setValidator(val)
        min.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        min.setObjectName('Min')

        labelMax = QLabel()        
        labelMax.setText("Max:")
        labelMax.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        
        max = QLineEdit()
        max.setText(self.runModule.max)
        max.setValidator(val)
        max.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        max.setObjectName('Max')
        
        layout = QGridLayout()
        layout.setContentsMargins(5, 5, 5, 5)
        layout.addWidget(labelData, 0, 0)
        layout.addWidget(dataSelection, 0, 1, 1, 5)
        layout.addWidget(labelEnergy, 1, 0)
        layout.addWidget(energy, 1, 1)
        layout.addWidget(labelDetector, 1, 2)
        layout.addWidget(detector, 1, 3)
        layout.addWidget(labelTarget, 1, 4)
        layout.addWidget(target, 1, 5)
        layout.addWidget(setButton, 1, 6)
        layout.addWidget(setOK, 2, 6)
        layout.addWidget(labelBins, 2, 0)
        layout.addWidget(bins, 2, 1)
        layout.addWidget(labelMin, 2, 2)
        layout.addWidget(min, 2, 3)
        layout.addWidget(labelMax, 2, 4)
        layout.addWidget(max, 2, 5)
        self.settingsWindow.setLayout(layout)

def main(argv = None):
    
    if argv == None:
        argv = sys.argv[1:]
        
    usage = "usage: %prog [options]\n Future Collider Experiment emulator"
    
    parser = OptionParser(usage)
    parser.add_option("--getdata",
                      default='',
                      choices=['', 'IDEA_91', 'IDEA_160', 'IDEA_240', 'IDEA_365', 'CLD_91', 'CLD_160', 'CLD_240', 'CLD_365'],
                      help="Dataset name to download [default: %default]")
    parser.add_option("--output", default='datasets', help="Output directory to store datasets [default: %default]")
    
    (options, args) = parser.parse_args(sys.argv[1:])
    
    if options.getdata == '':
    
        app = QApplication(sys.argv)
        screen = app.screens()[0]
        dpi = int(screen.physicalDotsPerInch()*1.5)
        evt = threading.Event()
        runModule = RunModule(evt, dpi)
        
        gallery = WidgetGallery(runModule, app)
        gallery.show()
        runMonitor = RunMonitor(runModule, gallery)
        runMonitor.start()
        sys.exit(app.exec())
        
    else:
        
        dn = options.getdata.split('_')
        det = dn[0]
        en = dn[1]
        loc = 'https://homepage.iihe.ac.be/~kskovpen/fce/datasets'
        dir = det+'/'+en+'GeV'
        os.system('rm -rf '+options.output+'/'+dir+'; mkdir -p '+options.output+'/'+dir)
        os.system('wget --recursive -nd --no-parent -R "index.html*" '+loc+'/'+dir+'/ -P '+options.output+'/'+dir)

if __name__ == '__main__':

    main()