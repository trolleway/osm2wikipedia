# -*- coding: utf-8 -*-
"""
/***************************************************************************
 osm2wikipedia
                                 A QGIS plugin
 Convert .osm.pbf dump to geopackage with Wikipedia map styles
 Generated by Plugin Builder: http://g-sherman.github.io/Qgis-Plugin-Builder/
                              -------------------
        begin                : 2021-09-26
        git sha              : $Format:%H$
        copyright            : (C) 2021 by Artem Svetlov
        email                : trolleway@yandex.ru
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
from qgis.PyQt.QtCore import QSettings, QTranslator, QCoreApplication
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction, QFileDialog

from qgis.core import QgsProject, QgsMessageLog, QgsVectorLayer, QgsCoordinateReferenceSystem

# Initialize Qt resources from file resources.py
from .resources import *
# Import the code for the dialog
from .osm2wikipedia_dialog import osm2wikipediaDialog
import os.path

from osgeo import ogr, gdal, osr
import datetime


class osm2wikipedia:
    """QGIS Plugin Implementation."""

    def __init__(self, iface):
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """
        # Save reference to the QGIS interface
        self.iface = iface
        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)
        # initialize locale
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'osm2wikipedia_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)
            QCoreApplication.installTranslator(self.translator)

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&osm2wikipedia')

        # Check if plugin was started the first time in current QGIS session
        # Must be set in initGui() to survive plugin reloads
        self.first_start = None
    
    def __del__(self):
        pass

    # noinspection PyMethodMayBeStatic
    def tr(self, message):
        """Get the translation for a string using Qt translation API.

        We implement this ourselves since we do not inherit QObject.

        :param message: String for translation.
        :type message: str, QString

        :returns: Translated version of message.
        :rtype: QString
        """
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate('osm2wikipedia', message)


    def add_action(
        self,
        icon_path,
        text,
        callback,
        enabled_flag=True,
        add_to_menu=True,
        add_to_toolbar=True,
        status_tip=None,
        whats_this=None,
        parent=None):
        """Add a toolbar icon to the toolbar.

        :param icon_path: Path to the icon for this action. Can be a resource
            path (e.g. ':/plugins/foo/bar.png') or a normal file system path.
        :type icon_path: str

        :param text: Text that should be shown in menu items for this action.
        :type text: str

        :param callback: Function to be called when the action is triggered.
        :type callback: function

        :param enabled_flag: A flag indicating if the action should be enabled
            by default. Defaults to True.
        :type enabled_flag: bool

        :param add_to_menu: Flag indicating whether the action should also
            be added to the menu. Defaults to True.
        :type add_to_menu: bool

        :param add_to_toolbar: Flag indicating whether the action should also
            be added to the toolbar. Defaults to True.
        :type add_to_toolbar: bool

        :param status_tip: Optional text to show in a popup when mouse pointer
            hovers over the action.
        :type status_tip: str

        :param parent: Parent widget for the new action. Defaults None.
        :type parent: QWidget

        :param whats_this: Optional text to show in the status bar when the
            mouse pointer hovers over the action.

        :returns: The action that was created. Note that the action is also
            added to self.actions list.
        :rtype: QAction
        """

        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            # Adds plugin icon to Plugins toolbar
            self.iface.addToolBarIcon(action)

        if add_to_menu:
            self.iface.addPluginToMenu(
                self.menu,
                action)

        self.actions.append(action)

        return action

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        icon_path = ':/plugins/osm2wikipedia/icon.png'
        self.add_action(
            icon_path,
            text=self.tr(u'Convert OSM dump to map for Wikipedia'),
            callback=self.run,
            parent=self.iface.mainWindow())

        # will be set False in run()
        self.first_start = True


    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginMenu(
                self.tr(u'&osm2wikipedia'),
                action)
            self.iface.removeToolBarIcon(action)

    def select_input_pbf(self):
        input_filename_1, _filter = QFileDialog.getOpenFileName(
        self.dlg, "Select source OSM dump file ","", '*.pbf')
        self.dlg.lineEdit.setText(filename)
        return input_filename_1
        
    def copy_layer2file(self, drivername, input_ds, input_layer, layername, filename):

        if os.path.isfile(filename): os.unlink(filename)

        out_driver = ogr.GetDriverByName(drivername)
        output_data_source = out_driver.CreateDataSource(filename)
        
        dest_layer = output_data_source.CopyLayer(input_layer,layername)
        if drivername == 'ESRI Shapefile':
            with open(filename.replace('.shp','.cpg'), 'w') as f:
                f.write('UTF-8')
        dest_layer = None
        output_data_source = None   
        out_driver = None
    def calc_area(self,wkb_geom):
        # Calculate area of geometry.
        # Source: geometry in 4326
                
        #if ogr.GetGeometryType(ogr.CreateGeometryFromWkb(wkb_geom)) == ogr.wkbMultiPolygon:
        centroid = ogr.CreateGeometryFromWkb(wkb_geom).Centroid()
        #magic numbers 
        x = int(centroid.GetX() // 6)
        zone = x + 31
        epsg_utm = zone + 32600
        if int(centroid.GetX()) < 0 : 
            epsg_utm = zone + 32700 #south hemisphere
            
        #reproject area from ngw's 3857 to UTM
        source = osr.SpatialReference()
        source.ImportFromEPSG(4326)

        target = osr.SpatialReference()
        target.ImportFromEPSG(epsg_utm)

        transform = osr.CoordinateTransformation(source, target)
        geom_4326 = ogr.CreateGeometryFromWkb(wkb_geom)
        geom_4326.Transform(transform)
        geom_utm = geom_4326
        return geom_utm.GetArea()

    
    def pbf2gpkg(self, filepath, water_polygons_path=''):
          
        gdal.UseExceptions()    
        
       
        driver_name = "OSM"
        driver = ogr.GetDriverByName(driver_name)
        if driver is None:
            msg = ("%s driver not available.\n" % driver_name)
        else:
            msg = ( "%s driver available.\n" % driver_name)
            ogr_driver_enabled = True
        assert ogr_driver_enabled == True
        

        config_file = os.path.join(os.path.dirname(os.path.realpath(__file__)),'osmconf_wikipedia.ini')
        assert os.path.isfile(config_file) 
        gdal.SetConfigOption('OSM_CONFIG_FILE', config_file)
        assert os.path.isfile(filepath) 
        
        result_files_dir = os.path.join(os.path.dirname(filepath), 'osm2wikipedia_data_'+datetime.datetime.today().strftime('%Y-%m-%d-%H%M'))
        if not os.path.exists(result_files_dir):
            os.makedirs(result_files_dir)
        assert os.path.isdir(result_files_dir)

        ds = gdal.OpenEx(filepath, gdal.OF_READONLY)#, allowed_drivers=['osm'])      
        assert ds is not None
        
        layer_pbf = ds.GetLayer('multipolygons')
        feat = layer_pbf.GetNextFeature()
        assert feat is not None

        # Background layer generation
        ring = ogr.Geometry(ogr.wkbLinearRing)
        ring.AddPoint(-179.99, 89.99)
        ring.AddPoint(179.99, 89.99)
        ring.AddPoint(179.99, -89.99)
        ring.AddPoint(-179.99, -89.99)
        ring.AddPoint(-179.99, 89.99)
        poly = ogr.Geometry(ogr.wkbPolygon)
        poly.AddGeometry(ring)
        
        layer_filename = os.path.join(result_files_dir,'background.geojson')
        background_ds = ogr.GetDriverByName('GeoJSON').CreateDataSource(layer_filename)
        assert background_ds is not None, ('Unable to create %s.' % layer_filename)
        background_layer = background_ds.CreateLayer("background", geom_type=ogr.wkbPolygon)
        featureDefn = background_layer.GetLayerDefn()
        feature = ogr.Feature(featureDefn)
        feature.SetGeometry(poly)
        background_layer.CreateFeature(feature)
        del feature
        del background_layer
        del background_ds
        qgis_layer = QgsVectorLayer(layer_filename, "Map background", "ogr")
        if qgis_layer.isValid():  
            qgis_loaded_layer = QgsProject.instance().addMapLayer(qgis_layer)
            qgis_loaded_layer.loadNamedStyle(os.path.join(self.plugin_dir,'styles','land.qml'))

        # water-polygons (oceans coastlines data)
        if os.path.isfile(water_polygons_path):
            qgis_layer = QgsVectorLayer(water_polygons_path, "Oceans", "ogr")
            if qgis_layer.isValid():  
                qgis_loaded_layer = QgsProject.instance().addMapLayer(qgis_layer)
                qgis_loaded_layer.loadNamedStyle(os.path.join(self.plugin_dir,'styles','oceans.qml'))       

        # water-polygons
        
        driver_mem = ogr.GetDriverByName('MEMORY')
        ds_mem = driver_mem.CreateDataSource('memData')
        driver_mem.Open('memData',1) 
        
        ds_mem = ogr.GetDriverByName('Memory').CreateDataSource('')
        
        layer_pbf.SetAttributeFilter("natural in ('water') or waterway='riverbank'")
        layer_pbf.ResetReading()
        memory_layer = ds_mem.CopyLayer(layer_pbf,'water-polygons')
        assert memory_layer is not None
        assert memory_layer.GetFeatureCount()>0
        assert memory_layer.GetFeatureCount()>0
        memory_layer.CreateField(ogr.FieldDefn("area", ogr.OFTReal))
        defn = memory_layer.GetLayerDefn()

        
        memory_layer.ResetReading()
        for i in range(0, memory_layer.GetFeatureCount()):
            feature = memory_layer.GetNextFeature()
        
            geom = feature.GetGeometryRef()
            feature.SetField('area',round(self.calc_area(feature.GetGeometryRef().ExportToWkb())/100000,2))
            #feature.SetField('name','чурка')
            memory_layer.SetFeature(feature)
            feature = None
        layer_filename = os.path.join(result_files_dir,'water-polygons.geojson')
        self.copy_layer2file('GeoJSON',ds_mem, memory_layer, 'water-polygons', layer_filename)
        qgis_layer = QgsVectorLayer(layer_filename, "water", "ogr")
        if qgis_layer.isValid():  
            qgis_loaded_layer = QgsProject.instance().addMapLayer(qgis_layer)
            qgis_loaded_layer.loadNamedStyle(os.path.join(self.plugin_dir,'styles','water-polygon-byarea.qml'))  
        del ds_mem
        # landuse
        
        
        layer_pbf.SetAttributeFilter("landuse in ('residential','industrial','commercial','retail')")
        layer_pbf.ResetReading()
        layer_filename = os.path.join(result_files_dir,'build area.geojson')
        self.copy_layer2file('GeoJSON',ds, layer_pbf, 'build area', layer_filename)
        qgis_layer = QgsVectorLayer(layer_filename, "Build area", "ogr")
        if qgis_layer.isValid():  
            qgis_loaded_layer = QgsProject.instance().addMapLayer(qgis_layer)
            qgis_loaded_layer.loadNamedStyle(os.path.join(self.plugin_dir,'styles','build area.qml'))   
        
        layer_pbf = ds.GetLayer('lines')
        feat = layer_pbf.GetNextFeature()
        assert feat is not None


        #layer = ds_mem.CopyLayer(ds.GetLayer('lines'),'lines',['OVERWRITE=YES'])
        
        layer_pbf.SetAttributeFilter("highway IS NOT NULL AND highway NOT IN ( 'track','service','footway','path')")
        layer_pbf.ResetReading()
        layer_filename = os.path.join(result_files_dir,'highways_filtered.geojson')
        self.copy_layer2file('GeoJSON',ds, layer_pbf, 'highways', layer_filename)
        qgis_layer = QgsVectorLayer(layer_filename, "Highways", "ogr")
        if qgis_layer.isValid():  
            qgis_loaded_layer = QgsProject.instance().addMapLayer(qgis_layer)
            qgis_loaded_layer.loadNamedStyle(os.path.join(self.plugin_dir,'styles','highways.qml'))   

        (xmin, xmax, ymin, ymax) = layer_pbf.GetExtent()
        ring = ogr.Geometry(ogr.wkbLinearRing)
        ring.AddPoint(xmin, ymax)
        ring.AddPoint(xmax, ymax)
        ring.AddPoint(xmax, ymin)
        ring.AddPoint(xmin, ymin)
        ring.AddPoint(xmin, ymax)
        poly = ogr.Geometry(ogr.wkbPolygon)
        poly.AddGeometry(ring)
        centroid = poly.Centroid()
        assert centroid is not None
            
        layer_pbf.SetAttributeFilter("railway = 'rail' and service not in ('siding','yard','spur')")
        layer_pbf.ResetReading()
        layer_filename = os.path.join(result_files_dir,'hrailways_major.geojson')
        self.copy_layer2file('GeoJSON',ds, layer_pbf, 'railways', layer_filename)
        qgis_layer = QgsVectorLayer(layer_filename, "Railways major", "ogr")
        if qgis_layer.isValid():  
            qgis_loaded_layer = QgsProject.instance().addMapLayer(qgis_layer)
            qgis_loaded_layer.loadNamedStyle(os.path.join(self.plugin_dir,'styles','railways.qml'))
        del qgis_layer
        del layer_filename
        
        #markers layer
                
        layer_filename = os.path.join(result_files_dir,'markers.geojson')
        markers_ds = ogr.GetDriverByName('GeoJSON').CreateDataSource(layer_filename)
        assert markers_ds is not None, ('Unable to create %s.' % layer_filename)
        markers_layer = markers_ds.CreateLayer("markers", geom_type=ogr.wkbPoint)
        markers_layer.CreateField(ogr.FieldDefn("name_loc", ogr.OFTString))
        markers_layer.CreateField(ogr.FieldDefn("name_int", ogr.OFTString))
        featureDefn = markers_layer.GetLayerDefn()
        feature = ogr.Feature(featureDefn)
        #feature.SetGeometry(ogr.CreateGeometryFromWkt('POINT (37.666 55.666)'))
        feature.SetGeometry(centroid)
        feature.SetField("name_loc", 'Маркер. Сдвиньте и переименуйте')
        feature.SetField("name_int", 'Marker. Move and rename')
        markers_layer.CreateFeature(feature)
        del feature
        del markers_layer
        del markers_ds
        qgis_layer = QgsVectorLayer(layer_filename, "markers", "ogr")
        if qgis_layer.isValid():  
            qgis_loaded_layer = QgsProject.instance().addMapLayer(qgis_layer)
            qgis_loaded_layer.loadNamedStyle(os.path.join(self.plugin_dir,'styles','markers.qml'))

        
     

        
        #QgsProject.instance().setCrs(QgsCoordinateReferenceSystem(3857))
        
    def run(self):
        """Run method that performs all the real work"""

        # Create the dialog with elements (after translation) and keep reference
        # Only create GUI ONCE in callback, so that it will only load when the plugin is started
        if self.first_start == True:
            self.first_start = False
            self.dlg = osm2wikipediaDialog()
            #self.dlg.pushButton.clicked.connect(self.select_input_pbf)

        #call file select dialog at module start, for minimize clicks count
        #filename = self.select_input_pbf()
            
        # show the dialog
        self.dlg.show()
        # Run the dialog event loop
        result = self.dlg.exec_()
        
        
        # See if OK was pressed
        if result:
            # Do something useful here - delete the line containing pass and
            # substitute with your code.
            #filename = ''
            #filename = self.dlg.mQgsFileWidget.text()
            input_filename_2 = ''
            input_filename_1 = self.dlg.mQgsFileWidget.filePath()
            input_filename_2 = self.dlg.mQgsFileWidget_2.filePath()
            if os.path.isfile(input_filename_1): 
                self.pbf2gpkg(input_filename_1,input_filename_2)
            else:
                QgsMessageLog.logMessage('Dump not found: '+input_filename_1, 'osm2wikipedia')
            pass
