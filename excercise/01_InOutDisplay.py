from traits.api import *
from traitsui.api import *
from math import *
import numpy as np
from random import *
from chaco.api import *
from enable.component_editor import ComponentEditor


class InOutDisplay(HasTraits):
	UP=Button(label=u'\u2191')
	DOWN=Button(label=u'\u2193')
	graph = Button(label="Plot this")
	plot = Instance(Plot)
	Input = Int()
	Output = Int(128)
	Maximum = Int()
	findMax = Button(label="Find Maximum")
	pixel = np.linspace(1,1024,1024)
	values = np.linspace(1,1024,1024)
	data = [[pixel],[values]]

	view=View(HGroup(VGroup(Item("Input", show_label=False, style="custom"),Item("Output", show_label=False, style="custom")),VGroup(Item("findMax", show_label=False, springy=False),Item("UP", show_label=False, resizable = False, springy=False), Item("DOWN", show_label=False, resizable=False, springy=False)),VGroup(Item("plot",editor=ComponentEditor(),show_label=False))),width=600,height=600, resizable=True)

	def _UP_fired(self):
		if not self.Output == 255:
			self.Output +=1
			self.values = [randint(1,100000) for i in self.values]
		else:
			print "end of range"
	def _DOWN_fired(self):
		if not self.Output == 0:
			self.Output -=1
			self.values = [randint(1,100000) for i in self.values] 
		else:
			print "end of range"
	def _findMax_fired(self):
		self.Maximum = int(self.values[0])
		posx = Int()
		for i in range(0,1024):
			if self.Maximum < self.values[i]:
				self.Maximum = int(self.values[i])
				posx = i
		self.Input = self.Maximum
#	def __init__(self):
#		super(InOutDisplay, self).__init__()

		x = self.pixel
		y = self.values
		mx = [posx,posx]
		my = [0,100000]
		plotdata = ArrayPlotData(x=x, y=y, mx=mx, my=my)
		plot = Plot(plotdata)
		plot.plot(("x","y"),type="line",color="blue")
		plot.plot(("mx","my"),type="line",color="red")
#		plotdata = ArrayPlotData(x=mx, y=my)
#		plot= Plot(plotdata)
#		plot.plot(("mx","my"),type="line",color="red")
		plot.title = "Random Data"
		self.plot = plot

InOutDisplay().configure_traits()