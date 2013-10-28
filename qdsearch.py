#!/usr/bin/env python
# -*- coding: utf-8 -*-

from traits.api import *
from traitsui.api import *
from traitsui.menu import OKButton, CancelButton
import thread
from pyface.api import information
import time
import math
#from ctypes import *
import pickle
import numpy as np
from threading import Thread
from enable.api import BaseTool
from time import sleep

from chaco.api import Plot, ArrayPlotData

from enable.component_editor import ComponentEditor

from chaco.tools.api import PanTool, ZoomTool

from traitsui.file_dialog import open_file,save_file

import views.cryo
reload(views.cryo)

import views.spectrometer
reload (views.spectrometer)

import views.camera
reload (views.camera)

import views.voltage
reload (views.voltage)

"""events on the plot"""
class PlotTool(BaseTool):
    def normal_left_dclick(self, event):
        [x,y]=self.component.map_data((event.x,event.y))
        main.move_cryo(x,y)

    def normal_mouse_move(self,event):
        [x,y]=self.component.map_data((event.x,event.y))
        main.plot_spectrum(x,y,'current')

    def normal_right_down(self,event):
        print "right mouse"
        [x,y]=self.component.map_data((event.x,event.y))
        main.plot_spectrum(x,y,'compare')

class counts_thread(Thread):
    def run(self):
        while not self.wants_abort:
            self.caller.counts = self.caller.ispectrometer.ivolt.measure()/self.VoltPerCount

class MainWindow(HasTraits):
    VoltPerCount = 0.002 # 2mv/Count


    """for creating the menu"""
    call_menu_scan_sample=Action(name='scansample',action='call_scan_sample_menu')
    save_to=Action(name='Save as',action='save_to')
    open_to=Action(name='open...',action='open_to')
    reload_all=Action(name='reload modules',action='reload_all')
    file_menu = Menu(save_to,open_to,reload_all, CloseAction,name='File')
    scan_sample_menu=Menu(call_menu_scan_sample,name='scan_sample')
    file_name=File('measurement/spectra.pick')

    """for setting"""
    toleranz=CFloat(0.001,desc='gives the toleranzradius for mouse move and click on the plot ')
    offset=CFloat(12)

    """for scanning sample"""
    textfield=Str()
    x1=CFloat(2.05)
    x2=CFloat(2.15)
    y1=CFloat(2.1)
    y2=CFloat(2.2)
    x_stepsize=CFloat(0.025)
    y_stepsize=CFloat(0.025)
    threshold_counts=CFloat(2000)
    counts=CFloat(125)
    scan_sample=Button()
    scan_sample_step=Button()
    abort=Button()
    finished=True
    x_koords=[]
    y_koords=[]
    spectra=[]
    wavelength=CFloat(0)
    plot=Instance(Plot,())
    plot_current=Instance(Plot,())
    plot_compare=Instance(Plot,())

    counts_thread = counts_thread()
    ispectrometer = Instance(views.spectrometer.SpectrometerGUI,() ) 
    icryo         = Instance(views.cryo.CryoGUI,())
    ivoltage      = Instance(views.voltage.VoltageGUI,())

    icamera       = Instance(views.camera.CameraGUI)# No ",()" as below, Instance is created in _default


    def _icamera_default(self):
        return views.camera.CameraGUI(icryo=self.icryo, ivoltage=self.ivoltage)

    hide_during_scan = { 'enabled_when': 'finished==True'}
    hide_no_scan = { 'enabled_when': 'finished==False'}
    hide = { 'enabled_when': 'False'}

    scan_ctrl=VGroup(
            Item('textfield',label='Scan from / to / stepsize [mm]',style='readonly'),
            HGroup(Item('x1',label='x'),
                   Item('x2',show_label=False),
                   Item('x_stepsize',show_label=False,label='width step (x) [mm]  '),
                   Item('counts',label='counts',editor=TextEditor(format_str='%5.0f', evaluate=float),**hide),
                   Item('threshold_counts',label='threshold',editor=TextEditor(format_str='%5.0f', evaluate=float)),
                   **hide_during_scan
                  ),
            HGroup(Item('y1',label='y',**hide_during_scan),
                   Item('y2',show_label=False,label='y2 [mm]',**hide_during_scan),
                   Item('y_stepsize',show_label=False,label='height step (y) [mm] ',**hide_during_scan),
                   Item('scan_sample_step',label='Scan',show_label=False,**hide_during_scan),
                   Item('abort',show_label=False,**hide_no_scan),
                  ))

    scan_sample_group=HGroup(
          VGroup(
              Item('plot',editor=ComponentEditor(size=(200,200)),show_label=False),
              scan_ctrl
              ),
          VGroup(Item('plot_current',editor=ComponentEditor(size=(100,200)),show_label=False),
                 Item('plot_compare',editor=ComponentEditor(size=(100,200)),show_label=False)
                ),
         label='scan sample'
          )

    spectrometer_tab = VGroup(
            Item('ispectrometer', style = 'custom',show_label=False),
            Item('icamera',style = 'custom', show_label=False),
            label='spectrometer'
            )

    focus_tab = VGroup(
            Item('icamera',style = 'custom', show_label=False),
            Item('icryo', style = 'custom',show_label=False,label="cryo", enabled_when='finished==True'),
            Item('ivoltage', style='custom',show_label=False,label="voltage"),
            label='Focus'
            )


    tabs = Group(
        Item('icryo', style = 'custom',show_label=False,label="cryo", enabled_when='finished==True'),
        spectrometer_tab,
        scan_sample_group,
        focus_tab,
        layout='tabbed')

    traits_view = View(
        tabs,
     menubar=MenuBar(file_menu,views.cryo.CryoGUI.menu,scan_sample_menu),
    title   = 'qdsearch',
    buttons = [ 'OK' ],
    resizable = True
    )

    setting_view=View(Item('toleranz'),Item('offset'),
                        buttons = [OKButton, CancelButton,],
                        kind='livemodal')

    def __init__(self,*args,**kwargs):
        self.initkwargs=kwargs
        self.initargs=args
        super(MainWindow,self).__init__(*self.initargs,**self.initkwargs)
        self.run_counts_thread()

    def run_counts_thread(self):
        self.counts_thread.wants_abort = False
        self.counts_thread.caller = self
        self.counts_thread.VoltPerCount = self.VoltPerCount
        self.counts_thread.start()

    def call_cryo_menu(self):
       self.icryo.configure_traits(view='view_menu')

    def call_spectrometer_menu(self):
       self.ispectrometer.configure_traits(view='view_menu')

    def call_scan_sample_menu(self):
        self.configure_traits(view='setting_view')

    def _scan_sample_step_fired(self):
        if self.ispectrometer.measurement_process or self.ispectrometer.acquisition_process:
            information(parent=None,title='please wait', message='Measurement at the spectrometer is running please finish this first.')
        else:
            thread.start_new_thread(self.scanning_step,())

    def scanning_step(self):

        if self.icamera.camera.init_active:
            information(parent=None, title="please wait",
             message="The initialization of the camera is running. " + \
             "Please wait until the initialization is finished.")
            return False

        #self.icryo.cryo.cryo_refresh=False
        self.finished=False
        self.x_koords=[]
        self.y_koords=[]
        self.spectra=[]

        if self.x1>self.x2:
            self.x2,self.x1 = self.x1,self.x2

        if self.y1>self.y2:
            self.y1,self.y2=self.y2,self.y1

        f = open('measurement/last_measurement.pick', "w") # creates new file
        f.close()


        if self.ispectrometer.exit_mirror=='front (CCD)': #ueberprueft ob spiegel umgeklappt bzw falls nicht klappt er ihn um
             self.ispectrometer.exit_mirror='side (APDs)'#self.ispectrometer.exit_mirror_value[1

        self.icryo.cryo.waiting() #wartet bis cryo bereit

        #TODO das hier gehört nach cryo
        # [x,y] = self.icryo.cryo.get_numeric_position()
        #x,y=self.icryo.cryo.convert_output(self.icryo.cryo.position())

        x_pos,y_pos = self.calc_snake_xy_pos()

        for i in range(len(x_pos)):
            if self.finished:
                break # abort condition
            self.icryo.cryo.move(x_pos[i],y_pos[i])
            self.icryo.cryo.waiting()
            # get actuall position, maybe x_pos[i] != x
            x,y=self.icryo.cryo.pos()
            if self.threshold_counts < self.ispectrometer.ivolt.measure()/self.VoltPerCount: # vergleicht schwellenspannung mit aktueller
                self.take_spectrum(x,y)
            self.plot_map(x,y)

        self.finished = True
        print 'searching finish'


    def _abort_fired(self):
        self.finished=True
        self.icryo.cryo.stop() #stopt cryo
        print 'abort'

    def take_spectrum(self,x,y):
        print "nehme spektrum, warte auf klappspiegel"
        self.ispectrometer.exit_mirror='front (CCD)' # klappt spiegel vom spectro auf kamera um
        time.sleep(1) # don't switch mirrors too fast!
        c_spectrum=self.icamera.camera.acquisition() # nimmt das spektrum auf

        spectrum=[]
        for i in range(len(c_spectrum)):
            spectrum.append(c_spectrum[i])

        self.ispectrometer.exit_mirror='side (APDs)' # klappt spiegel vom spectro auf ausgang um

        # warning: we don't check if we are still at the same position!

        self.x_koords.append(x)
        self.y_koords.append(y)
        self.spectra.append(spectrum)
        self.add_to_file(x,y,spectrum)

    def add_to_file(self,x,y,spectrum):
        f = open('measurement/last_measurement.pick', "a")
        pickle.dump([x,y,spectrum],f)
        f.close()

    def reload_all(self):
        import pdb;pdb.set_trace()

    def plot_map(self,x,y):
        plotdata = ArrayPlotData(x=self.x_koords, y=self.y_koords,x2=[x],y2=[y])
        plot = Plot(plotdata)
        plot.plot(("x", "y"), type="scatter", color="blue")
        plot.title = ""
        plot.overlays.append(ZoomTool(component=plot,tool_mode="box", always_on=False))
        plot.tools.append(PanTool(plot, constrain_key="shift"))
        plot.tools.append(PlotTool(component=plot))
        plot.plot(('x2','y2'),type='scatter',color='red')
        plot.range2d.x_range.low=self.x1
        plot.range2d.x_range.high=self.x2
        plot.range2d.y_range.low=self.y1
        plot.range2d.y_range.high=self.y2
        plot.x_axis.title="x-Position on sample [mm]"
        plot.y_axis.title="y-Position on sample [mm]"
        self.plot=plot

    def calculate_dispersion(self,wavelength,grooves):
        m=1 #grating order
        x=8.548 #spectro value: half angle
        f=486 # focal length
        phi=math.degrees(math.asin((m*wavelength*grooves/(2*10**6*math.cos(math.radians(x))))))
        dispersion=math.cos(math.radians(x+phi))*10**6/(grooves*f*m)
        return dispersion

    def create_wavelength_for_plotting(self):
        wavelength=[]
        pixel=1024
        grooves=self.ispectrometer.current_grating.split(' ')
        grooves=int([x for x in grooves if x][1])
        for i in range(pixel+1):
            wavelength.append(i)
        width=26*10**-3
        wavelength[pixel/2]=self.ispectrometer.centerwvl
        for i in range(pixel/2):
            wavelength[pixel/2-i-1]=wavelength[pixel/2-i]-width*self.calculate_dispersion(wavelength[pixel/2-i],grooves)
            wavelength[pixel/2+i+1]=wavelength[pixel/2+i]+width*self.calculate_dispersion(wavelength[pixel/2+i],grooves)
        return wavelength


    def plot_spectrum(self,x,y,field):
        for i in range(len(self.x_koords)):
            x_gap=abs(x-self.x_koords[i])
            y_gap=abs(y-self.y_koords[i])
            if x_gap <self.toleranz and y_gap<self.toleranz:
                spectrum=self.spectra[i]
                wavelength=self.create_wavelength_for_plotting()
                plotdata = ArrayPlotData(x=wavelength, y=spectrum)
                plot = Plot(plotdata)
                plot.plot(("x", "y"), type="line", color="blue")
                plot.x_axis.title="Wavelength [nm]"
                plot.y_axis.title="Counts"
                plot.title = 'spectrum of QD ' +str(self.x_koords[i])+' '+str(self.y_koords[i])
                plot.overlays.append(ZoomTool(component=plot,tool_mode="box", always_on=False)) # damit man im Plot zoomen kann
                plot.tools.append(PanTool(plot, constrain_key="shift")) # damit man mit der Maus den Plot verschieben kann
                if field=='current':
                    self.plot_current=plot
                if field=='compare':
                    self.plot_compare=plot

    def move_cryo(self,x,y):
        """looks whether a measured point is in the near of the plot event"""
        if self.finished:
            for i in range(len(self.x_koords)):
                x_gap=abs(x-self.x_koords[i])
                y_gap=abs(y-self.y_koords[i])
                if x_gap <self.toleranz and y_gap<self.toleranz:
                    self.icryo.cryo.move(self.x_koords[i],self.y_koords[i])
                    break

    def calc_snake_xy_pos(self):
        dist_x = abs(self.x2-self.x1)
        dist_y = abs(self.y2-self.y1)
        a = np.linspace(self.x1,self.x2,dist_x/self.x_stepsize)
        b = np.linspace(self.y1,self.y2,dist_y/self.y_stepsize) # hier war dist_y

        a = a.round(5)
        b = b.round(5)

        stepsa = len(a)
        stepsb = len(b)

        # we go snake-lines, so in the first y-step x=1,2 and in the
        # second y-step (the way back) x=2,1 .
        # Make a containing these two lines
        # a = [1,2] -> [1,2,2,1]
        a = np.array((a,np.flipud(a))).flatten()
        # repeat entire array a. This creates too many lines.
        a = np.tile  (a,stepsb)
        # within one line, y doesn't change, so repeat every element in b
        b = np.repeat(b,stepsa)
        #  discard unecessary elements in a
        a = np.resize(a,len(b))
        return [a,b]

    def save_to(self):
        file_name = save_file()
        print file_name
        if file_name != '':
            self.file_name = file_name
        self.save_file()

    def open_to(self):
        file_name = open_file()
        if file_name != '':
            self.file_name = file_name
        self.load()

    def save_file(self):
        f = open(self.file_name, "wb")

        data = {
            'cryo': {'x1':self.x1,
                     'x2':self.x2,
                     'y1':self.y1,
                     'y2':self.y2,
                     'x_stepsize':self.x_stepsize,
                     'y_stepsize':self.y_stepsize
                    },

            'spectrometer': { 'centerwvl': self.ispectrometer.centerwvl,
                              'grating': self.ispectrometer.current_grating,
                              'slot_width_in': self.ispectrometer.slot_width_in,
                              'slot_width_out': self.ispectrometer.slot_width_out
                            },
            'voltage': {
                    'threshold': self.threshold_counts
                    },

            'camera': {
                    'exposuretime':self.icamera.exposuretime,
                    'readmode':self.icamera.readmode,
                    'acquisitionmode':self.icamera.acquisitionmode,
                    'Vshiftspeed ':self.icamera.Vshiftspeed,
                    'Hshiftspeed ':self.icamera.Hshiftspeed
                    },

            'values': {
                    'x':self.x_koords,
                    'y':self.y_koords,
                    'spectra': self.spectra
                }
            }

        pickle.dump(data,f)
        f.close()

    def pop(self,data,device,key):

        if device in data:
            if key in data[device]:
                temp = data[device].pop(key)
                return temp
            else:
                error = 'no key ',key,' in device ',device
        else:
            error = 'no device ',device, ' in data'
        print error
        return None



    def load(self):
        f = open(self.file_name, "rb")
        data = pickle.load(f)
        f.close()

        self.x1 = self.pop(data,'cryo','x1')
        self.x2 = self.pop(data,'cryo','x2')
        self.y1 = self.pop(data,'cryo','y1')
        self.y2 = self.pop(data,'cryo','y2')
        self.x_stepsize = self.pop(data,'cryo','x_stepsize')
        self.y_stepsize = self.pop(data,'cryo','y_stepsize')

        self.ispectrometer.centerwvl = self.pop(data,'spectrometer','centerwvl')
        self.ispectrometer.current_grating = self.pop(data,'spectrometer','grating')
        self.ispectrometer.slot_width_in = self.pop(data,'spectrometer','slot_width_in')
        self.ispectrometer.slot_width_out = self.pop(data,'spectrometer','slot_width_out')

        self.threshold_counts = self.pop(data,'voltage','threshold')

        self.icamera.exposuretime = self.pop(data,'camera','exposuretime')
        self.icamera.readmode = self.pop(data,'camera','readmode')
        self.icamera.acquisitionmode = self.pop(data,'camera','acquisitionmode')
        self.icamera.Vshiftspeed = self.pop(data,'camera','Vshiftspeed ')
        self.icamera.Hshiftspeed = self.pop(data,'camera','Hshiftspeed ')

        self.x_koords = self.pop(data,'values','x')
        self.y_koords = self.pop(data,'values','y')
        self.spectra = self.pop(data,'values','spectra')

        self.plot_map(self.x_koords[0], self.y_koords[0])

        # raise load warning
        self.pop(data,'none','none')
        self.pop(data,'values','none')

        for device in data:
            for key in data[device]:
                print 'Did not load values from file:', device,key

main = MainWindow()
if __name__ == '__main__':
    main.configure_traits()
    main.icryo.open=False
    main.counts_thread.wants_abort=True
    sleep(1.0)

    if not main.icryo.cryo.simulation:
        print"close cryo"
        main.icryo.cryo.close()
        main.icryo.cryo_refresh=False
    if not main.ispectrometer.ispectro.simulation:
        print"close spectro"
        main.ispectrometer.ispectro.close()
    if not main.ispectrometer.ivolt.simulation:
        print"close Voltage"
        main.ispectrometer.ivolt.close()
    main.icamera.close()


