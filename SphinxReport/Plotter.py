"""Mixin classes for Renderers that plot.
"""

import os, sys, re, math

import matplotlib
import matplotlib.backends
import matplotlib.pyplot as plt
import numpy
import CorrespondenceAnalysis

class Plotter:
    """Base class for Renderers that do simple 2D plotting.

    This mixin class provides convenience function for :class:`Renderer.Renderer`
    classes that do 2D plotting.

    The base class takes care of counting the plots created,
    provided that the methods :meth:`startPlot` and :meth:`endPlot`
    are called appropriately. It then inserts the appropriate place holders.

    This class adds the following options to the :term:`render` directive:

       :term:`logscale`: apply logscales one or more axes.

       :term:`xtitle`: add a label to the X axis

       :term:`ytitle`: add a label to the Y axis

       :term:`title`: add a title to the plot

       :term:`legend-location`: specify the location of the legend

       :term:`as-lines`: do not plot symbols

       :term:`xrange`: restrict plot a part of the x-axis

       :term:`yrange`: restrict plot a part of the y-axis

    With some plots default layout options will result in plots 
    that are misaligned (legends truncated, etc.). To fix this it might
    be necessary to increase plot size, reduce font size, or others.
    The following options will be passed on the matplotlib to permit
    this control.

       :term:`mpl-figure`: options for matplotlib
           ``figure `` calls().

       :term:`mpl-legend`: options for matplotlib
           ``legend`` calls().

       :term:`mpl-subplot`: options for matplotlib
           ``subplots_adjust`` calls().

       :term:`mpl-rc`: general environment settings for matplotlib.
          See the matplotlib documentation. Multiple options can be
          separated by ;, for example 
          ``:mpl-rc: figure.figsize=(20,10);legend.fontsize=4``

    """

    mLegendFontSize = 8
    # number of chars to use to reduce legend font size
    mMaxLegendSize = 100

    ## maximum number of rows per column. If there are more,
    ## the legend is split into multiple columns
    mLegendMaxRowsPerColumn = 30

    def __init__(self, tracker ):
        self.mTracker = tracker

    def prepare(self, *args, **kwargs):
        """parse option arguments."""

        self.mFormat = "%i"
        self.mFigure = 0
        self.mColors = "bgrcmk"
        self.mSymbols = ["g-D","b-h","r-+","c-+","m-+","y-+","k-o","g-^","b-<","r->","c-D","m-h"]
        self.mMarkers = "so^>dph8+x"
        self.mXLabel = None
        self.mYLabel = None

        try: self.mLogScale = kwargs["logscale"]
        except KeyError: self.mLogScale = None

        try: self.mTitle = kwargs["title"]
        except KeyError: self.mTitle = None

        try: self.mXLabel = kwargs["xtitle"]
        except KeyError: 
            try: self.mXLabel = self.mTracker.getXLabel()
            except AttributeError: self.mXLabel = None

        try: self.mYLabel = kwargs["ytitle"]
        except KeyError: 
            try: self.mYLabel = self.mTracker.getYLabel()
            except AttributeError: self.mYLabel = None

        try: self.mLegendLocation = kwargs["legend-location"]
        except KeyError: self.mLegendLocation = "outer"

        try: self.mWidth = kwargs["width"]
        except KeyError: self.mWidth = 0.50

        self.mAsLines = "as-lines" in kwargs

        if self.mAsLines:
            self.mSymbols = []
            for y in ("-",":","--"):
                for x in "gbrcmyk":
                    self.mSymbols.append( y+x )

        try: self.mXRange = map(float, kwargs["xrange"].split(","))
        except: self.mXRange = None

        try: self.mYRange = map(float, kwargs["yrange"].split(","))
        except: self.mYRange = None

        def setupMPLOption( key ):
            options = {}
            try: 
                for k in kwargs[ key ].split(";"):
                    key,val = k.split("=")
                    # convert unicode to string
                    options[str(key)] = eval(val)
            except KeyError: 
                pass
            return options

        self.mMPLFigureOptions = setupMPLOption( "mpl-figure" )
        self.mMPLLegendOptions = setupMPLOption( "mpl-legend" )
        self.mMPLSubplotOptions = setupMPLOption( "mpl-subplot" )
        self.mMPLRC = setupMPLOption( "mpl-rc" )

    def startPlot( self, data, **kwargs ):
        """prepare everything for a plot."""

        self.mFigure +=1 

        # go to defaults
        matplotlib.rcdefaults()
        # set parameters
        matplotlib.rcParams.update(self.mMPLRC )
        
        plt.figure( num = self.mFigure, **self.mMPLFigureOptions )

        if self.mTitle:  plt.title( self.mTitle )
        if self.mXLabel: plt.xlabel( self.mXLabel )
        if self.mYLabel: plt.ylabel( self.mYLabel )

    def wrapText( self, text, cliplen = 20, separators = " :_" ):
        """wrap around text using the mathtext.

        Currently this subroutine uses the \frac 
        directive, so it is not pretty.
        returns the wrapped text."""
        
        # split txt into two equal parts trying
        # a list of separators
        newtext = []
        for txt in text:
            t = len(txt)
            if t > cliplen:
                for s in separators:
                    parts = txt.split( s )
                    if len(parts) < 2 : continue
                    c = 0
                    tt = t // 2
                    # collect first part such that length is 
                    # more than half
                    for x, p in enumerate( parts ):
                        if c > tt: break
                        c += len(p)

                    # accept if a good split (better than 2/3)
                    if float(c) / t < 0.66:
                        newtext.append( r"$\mathrm{\frac{ %s }{ %s }}$" % \
                                            ( s.join(parts[:x]), s.join(parts[x:])))
                        break
            else:
                newtext.append(txt)
        return newtext

    def endPlot( self, plts = None, legends = None, title = None ):
        """close a plot.

        Returns a list of restructured text with place holders for the current 
        figure.
        """

        if self.mXRange: plt.xlim( self.mXRange )
        if self.mYRange: plt.ylim( self.mYRange )

        if self.mLogScale:
            if "x" in self.mLogScale:
                plt.gca().set_xscale('log')
            if "y" in self.mLogScale:
                plt.gca().set_yscale('log')

        lines = [ "\n".join( ("## Figure %i ##" % self.mFigure, "")) ]

        legend = None
        maxlen = 0

        if title:
            plt.title( title )

        if self.mLegendLocation != "none" and plts and legends:

            maxlen = max( [ len(x) for x in legends ] )
            # legends = self.wrapText( legends )

            if self.mLegendLocation == "outer":
                legend = outer_legend( plts, legends )
            else:
                legend = plt.figlegend( plts, 
                                        legends,
                                        loc = self.mLegendLocation,
                                        **self.mMPLLegendOptions )


        if self.mLegendLocation == "extra" and legends:
            self.mFigure += 1
            legend = plt.figure( self.mFigure, **self.mMPLFigureOptions )
            lines.append( "\n".join( ("## Figure %i ##" % self.mFigure, "")) )
            lx = legend.add_axes( (0.1, 0.1, 0.9, 0.9) )
            lx.set_title( "Legend" )
            lx.set_axis_off()
            plt.setp( lx.get_xticklabels(), visible=False)
            if not plts:
                plts = []
                for x in legends:
                    plts.append( plt.plot( (0,), (0,) ) )

            lx.legend( plts, legends, 
                       'center left',
                       ncol = max(1,int(math.ceil( float( len(legends) / self.mLegendMaxRowsPerColumn ) ) )),
                       **self.mMPLLegendOptions )

        # smaller font size for large legends
        if legend and maxlen > self.mMaxLegendSize:
            ltext = legend.get_texts() # all the text.Text instance in the legend
            plt.setp(ltext, fontsize='small') 

        return lines

    def rescaleForVerticalLabels( self, labels, offset = 0.02, cliplen = 6 ):
        """rescale current plot so that vertical labels are displayed properly.

        In some plots the labels are clipped if the labels are vertical labels on the X-axis.
        This is a heuristic hack and is not guaranteed to always work.
        """
        # rescale plotting area if labels are more than 6 characters
        if len(labels) == 0: return

        maxlen = max( [ len(x) for x in labels ] )
        if maxlen > cliplen:
            currentAxes = plt.gca()
            currentAxesPos = currentAxes.get_position()

            # scale plot by 2% for each extra character
            # scale at most 30% as otherwise the plot will
            # become illegible (and matplotlib might crash)
            offset = min(0.3, offset * (maxlen- cliplen) )

            # move the x-axis up
            currentAxes.set_position((currentAxesPos.xmin,
                                      currentAxesPos.ymin + offset,
                                      currentAxesPos.width,
                                      currentAxesPos.height -offset))


class PlotterMatrix(Plotter):
    """Plot a matrix.

    This mixin class provides convenience function for :class:`Renderer.Renderer`
    classes that plot matrices.
    
    This class adds the following options to the :term:`render` directive:
    
       :term:`colorbar-format`: numerical format for the colorbar.

       :term:`palette`: numerical format for the colorbar.

       :term:`zrange`: restrict plot a part of the z-axis.

    """

    mFontSize = 8

    # after # characters, split into two
    # lines
    mSplitHeader = 20
    mFontSizeSplit = 8

    # separators to use to split text
    mSeparators = " :_"

    mMaxRows = 20
    mMaxCols = 20

    def __init__(self, *args, **kwargs ):
        Plotter.__init__(self, *args, **kwargs)

    def prepare( self,*args, **kwargs ):
        Plotter.prepare(self, *args, **kwargs)

        try: self.mBarFormat = kwargs["colorbar-format"]
        except KeyError: self.mBarFormat = "%1.1f"

        try: self.mPalette = kwargs["palette"]
        except KeyError: self.mPalette = "jet"

        try: self.mZRange = map(float, kwargs["zrange"].split(",") )
        except KeyError: self.mZRange = None

        self.mReversePalette = "reverse-palette" in kwargs

    def buildWrappedHeaders( self, headers ):
        """build headers. Long headers are split using
        the \frac mathtext directive (mathtext does not
        support multiline equations. 

        This method is currently not in use.

        returns (fontsize, headers)
        """

        fontsize = self.mFontSize
        maxlen = max( [ len(x) for x in headers ] )

        if maxlen > self.mSplitHeader:
            h = []
            fontsize = self.mFontSizeSplit

            for header in headers:
                if len(header) > self.mSplitHeader:
                    # split txt into two equal parts trying
                    # a list of separators
                    t = len(header)
                    for s in self.mSeparators:
                        parts= header.split( s )
                        if len(parts) < 2 : continue
                        c = 0
                        tt = t // 2
                        ## collect first part such that length is 
                        ## more than half
                        for x, p in enumerate( parts ):
                            if c > tt: break
                            c += len(p)

                        # accept if a good split (better than 2/3)
                        if float(c) / t < 0.66:
                            h.append( r"$\mathrm{\frac{ %s }{ %s }}$" % \
                                          ( s.join(parts[:x]), s.join(parts[x:])))
                            break
                    else:
                        h.append(header)
                else:
                    h.append(header)
            headers = h
            
        return fontsize, headers

    def plotMatrix( self, matrix, row_headers, col_headers ):

        self.startPlot( matrix )

        nrows, ncols = matrix.shape
        if self.mZRange:
            vmin, vmax = self.mZRange
            matrix[ matrix < vmin ] = vmin
            matrix[ matrix > vmax ] = vmax
        else:
            vmin, vmax = None, None

        if self.mPalette:
            if self.mReversePalette:
                color_scheme = eval( "plt.cm.%s_r" % self.mPalette)                    
            else:
                color_scheme = eval( "plt.cm.%s" % self.mPalette)
        else:
            color_scheme = None

        plots = []
        def addMatrix( matrix, row_headers, col_headers, vmin, vmax):

            plot = plt.imshow(matrix,
                              cmap=color_scheme,
                              origin='lower',
                              vmax = vmax,
                              vmin = vmin,
                              interpolation='nearest')

            # offset=0: x=center,y=center
            # offset=0.5: y=top/x=right
            offset = 0.0

            col_headers = [ str(x) for x in col_headers ]
            row_headers = [ str(x) for x in row_headers ]

            # determine fontsize for labels
            xfontsize, col_headers = self.mFontSize, col_headers
            yfontsize, row_headers = self.mFontSize, row_headers

            plt.xticks( [ offset + x for x in range(len(col_headers)) ],
                          col_headers,
                          rotation="vertical",
                          fontsize=xfontsize )

            plt.yticks( [ offset + y for y in range(len(row_headers)) ],
                          row_headers,
                          fontsize=yfontsize )
            
            return plot

        split_row, split_col = nrows > self.mMaxRows, ncols > self.mMaxCols

        if (split_row and split_col) or not (split_row or split_col):
            # do not split small or symmetric matrices
            addMatrix( matrix, row_headers, col_headers, vmin, vmax )
            plt.colorbar( format = self.mBarFormat)        
            plots, labels = None, None
            self.rescaleForVerticalLabels( col_headers, cliplen = 12 )

            if False:
                plot_nrows = int(math.ceil( float(nrows) / self.mMaxRows ))
                plot_ncols = int(math.ceil( float(ncols) / self.mMaxCols ))
                new_row_headers = [ "R%s" % (x + 1) for x in range(len(row_headers))]
                new_col_headers = [ "C%s" % (x + 1) for x in range(len(col_headers))]
                nplot = 1
                for row in range(plot_nrows):
                    for col in range(plot_ncols):
                        plt.subplot( plot_nrows, plot_ncols, nplot )
                        nplot += 1
                        row_start = row * self.mMaxRows
                        row_end = row_start+min(plot_nrows,self.mMaxRows)
                        col_start = col * self.mMaxRows
                        col_end = col_start+min(plot_ncols,self.mMaxCols)
                        addMatrix( matrix[row_start:row_end,col_start:col_end], 
                                   new_row_headers[row_start:row_end], 
                                   new_col_headers[col_start:col_end], 
                                   vmin, vmax )

                labels = ["%s: %s" % x for x in zip( new_headers, row_headers) ]
                self.mLegendLocation = "extra"
                plt.subplots_adjust( **self.mMPLSubplotOptions )

        elif split_row:
            if not self.mZRange:
                vmin, vmax = matrix.min(), matrix.max()
            nplots = int(math.ceil( float(nrows) / self.mMaxRows ))
            new_headers = [ "%s" % (x + 1) for x in range(len(row_headers))]
            for x in range(nplots):
                plt.subplot( 1, nplots, x+1 )
                start = x * self.mMaxRows
                end = start+min(nrows,self.mMaxRows)
                addMatrix( matrix[start:end,:], new_headers[start:end], col_headers, vmin, vmax )
            labels = ["%s: %s" % x for x in zip( new_headers, row_headers) ]
            self.mLegendLocation = "extra"
            plt.subplots_adjust( **self.mMPLSubplotOptions )
            plt.colorbar( format = self.mBarFormat)        

        elif split_col:
            if not self.mZRange:
                vmin, vmax = matrix.min(), matrix.max()
            nplots = int(math.ceil( float(ncols) / self.mMaxCols ))
            new_headers = [ "%s" % (x + 1) for x in range(len(col_headers))]
            for x in range(nplots):
                plt.subplot( nplots, 1, x+1 )
                start = x * self.mMaxCols
                end = start+min(ncols,self.mMaxCols)
                addMatrix( matrix[:,start:end], row_headers, new_headers[start:end], vmin, vmax ) 
            labels = ["%s: %s" % x for x in zip( new_headers, col_headers) ]
            self.mLegendLocation = "extra"
            plt.subplots_adjust( **self.mMPLSubplotOptions )
            plt.colorbar( format = self.mBarFormat)        

        return self.endPlot( plts = plots, legends = labels )

def outer_legend(*args, **kwargs):
    """plot legend outside of plot by rescaling it.

    Copied originally from http://www.mail-archive.com/matplotlib-users@lists.sourceforge.net/msg04256.html
    but modified.

    There were problems with the automatic re-scaling of the plot. Basically, the legend
    size seemed to be unknown and set to 0,0,1,1. Only after plotting were the correct
    bbox coordinates entered.

    The current implementation allocates 3/4 of the canvas for the legend and
    hopes for the best.
    """

    # make a legend without the location
    # remove the location setting from the kwargs
    if 'loc' in kwargs: kwargs.pop('loc')
    leg = plt.legend(loc=(0,0), *args, **kwargs)
    frame = leg.get_frame()
    currentAxes = plt.gca()
    currentAxesPos = currentAxes.get_position()

    # scale plot by the part which is taken by the legend
    plotScaling = 0.75

    # scale the plot
    currentAxes.set_position((currentAxesPos.xmin,
                              currentAxesPos.ymin,
                              currentAxesPos.width * (plotScaling),
                              currentAxesPos.height))

    # set (approximate) x and y coordinates of legend 
    leg._loc = (1 + .05, currentAxesPos.ymin )

    return leg
