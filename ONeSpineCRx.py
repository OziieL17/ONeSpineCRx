"""ONeSpineCRx scripted 3D Slicer module. See README for installation and limits."""
import json
import os
import qt
import ctk
import slicer
from slicer.ScriptedLoadableModule import ScriptedLoadableModule, ScriptedLoadableModuleWidget
from ONeSpineCRxLib.engine import LABELS, Projection, manual_scale, study, world_to_anatomical
from ONeSpineCRxLib.report import svg


class ONeSpineCRx(ScriptedLoadableModule):
    def __init__(self,parent):
        super().__init__(parent)
        self.parent.title='ONeSpineCRx'
        self.parent.categories=['ONe']
        self.parent.contributors=['Dr. Alexis Oziel Martínez Nava']
        self.parent.helpText='Análisis radiográfico cervical 2D guiado. Mediciones pendientes de revisión; versión 0.1.0.'
        self.parent.acknowledgementText='ONe — Neurocirugía'


class ONeSpineCRxWidget(ScriptedLoadableModuleWidget):
    def setup(self):
        super().setup()
        self.nodes={}; self.observers={}; self.volumes={}; self.settings={}; self.result=None
        self.busy=False; self.placing=False; self.calibrating=False; self.calibrationLengths={}; self.confirmedOrientations={}
        self.timer=qt.QTimer(); self.timer.setSingleShot(True); self.timer.setInterval(180)
        self.timer.connect('timeout()',self.calculate)
        self.layout.addWidget(qt.QLabel('ONeSpineCRx · Análisis cervical · v0.1.0'))
        group=ctk.ctkCollapsibleButton(); group.text='1–2 · Cargar y clasificar estudio'
        self.layout.addWidget(group); form=qt.QFormLayout(group)
        b=qt.QPushButton('Agregar DICOM'); form.addRow(b)
        b.connect('clicked()',lambda:slicer.util.selectModule('DICOM'))
        for name,title in [('lat','Lateral neutra'),('flex','Flexión'),('ext','Extensión')]:
            sel=slicer.qMRMLNodeComboBox(); sel.nodeTypes=['vtkMRMLScalarVolumeNode']; sel.noneEnabled=True
            sel.addEnabled=False; sel.removeEnabled=False; sel.setMRMLScene(slicer.mrmlScene)
            form.addRow(title,sel); self.volumes[name]=sel
            sel.connect('currentNodeChanged(vtkMRMLNode*)',lambda node,n=name:self.volumeChanged(n,node))
            self.settings[name]={'mm_per_unit':None,'horizontal_confirmed':False,'calibration_source':None,'posture':'unspecified'}
        self.active=qt.QComboBox(); self.active.addItems(['lat','flex','ext']); form.addRow('Proyección activa',self.active)
        self.active.connect('currentIndexChanged(int)',self.switchProjection)
        self.posture=qt.QComboBox(); self.posture.addItems(['unspecified','standing','seated','supine']); form.addRow('Posición de adquisición',self.posture)
        self.posture.connect('currentIndexChanged(int)',self.settingsChanged)
        group=ctk.ctkCollapsibleButton(); group.text='3 · Orientación y calibración'; self.layout.addWidget(group)
        form=qt.QFormLayout(group)
        info=qt.QLabel('Marque ORIGIN, luego ANTERIOR_REF hacia anterior y CRANIAL_REF hacia craneal.\nPara slopes/cSVA: ORIGIN→ANTERIOR_REF debe seguir la horizontal de adquisición.'); info.wordWrap=True; form.addRow(info)
        self.horizontal=qt.QCheckBox('Confirmo horizontal de adquisición y anterior/craneal'); form.addRow(self.horizontal)
        self.horizontal.connect('toggled(bool)',self.settingsChanged)
        self.length=qt.QDoubleSpinBox(); self.length.setRange(.01,1000); self.length.setValue(25); self.length.setSuffix(' mm'); form.addRow('Referencia conocida',self.length)
        b=qt.QPushButton('Marcar CAL_A y CAL_B'); form.addRow(b); b.connect('clicked()',self.startCalibration)
        b=qt.QPushButton('Aplicar referencia marcada'); form.addRow(b); b.connect('clicked()',self.calibrate)
        b=qt.QPushButton('Confirmar escala del volumen (RAS mm)'); form.addRow(b); b.connect('clicked()',self.confirmSpacing)
        self.scaleLabel=qt.QLabel('Sin calibración validada'); form.addRow(self.scaleLabel)
        group=ctk.ctkCollapsibleButton(); group.text='4 · Marcar anatomía'; self.layout.addWidget(group)
        form=qt.QFormLayout(group)
        self.nextLabel=qt.QLabel(); form.addRow(self.nextLabel)
        b=qt.QPushButton('Colocar siguiente punto'); form.addRow(b); b.connect('clicked()',self.placeNext)
        b=qt.QPushButton('Detener marcaje / editar puntos'); form.addRow(b); b.connect('clicked()',self.stopPlacement)
        b=qt.QPushButton('Abrir Markups para editar o eliminar'); form.addRow(b); b.connect('clicked()',lambda:slicer.util.selectModule('Markups'))
        tip=qt.QLabel('SA/SP: superior anterior/posterior · IA/IP: inferior anterior/posterior.\nC2–C7: cuatro esquinas. T1: platillo superior opcional. Osteofitos fuera del platillo no son esquinas.\nPuede omitir T1 y revisar resultados parciales.'); tip.wordWrap=True; form.addRow(tip)
        group=ctk.ctkCollapsibleButton(); group.text='5 · Revisar y exportar'; self.layout.addWidget(group)
        form=qt.QFormLayout(group)
        self.status=qt.QLabel('Esperando anatomía'); self.status.wordWrap=True; form.addRow(self.status)
        self.output=qt.QPlainTextEdit(); self.output.setReadOnly(True); self.output.setMinimumHeight(220); form.addRow(self.output)
        b=qt.QPushButton('Recalcular'); form.addRow(b); b.connect('clicked()',self.calculate)
        b=qt.QPushButton('Exportar JSON + figuras SVG'); form.addRow(b); b.connect('clicked()',self.export)
        b=qt.QPushButton('Restaurar sesión JSON'); form.addRow(b); b.connect('clicked()',self.restore)
        self.layout.addStretch(1); self.switchProjection()

    def name(self): return self.active.currentText

    def node(self,name):
        if name not in self.nodes:
            node=slicer.mrmlScene.AddNewNodeByClass('vtkMRMLMarkupsFiducialNode','ONeSpineCRx_'+name)
            node.CreateDefaultDisplayNodes(); node.SetAttribute('ONeSpineCRx.Projection',name)
            color={'lat':(0.1,.6,.7),'flex':(.8,.3,.6),'ext':(.4,.4,.9)}[name]
            node.GetDisplayNode().SetSelectedColor(*color)
            self.nodes[name]=node
            self.observers[name]=[node.AddObserver(slicer.vtkMRMLMarkupsNode.PointPositionDefinedEvent,lambda c,e,n=name:self.pointAdded(n)),
                                  node.AddObserver(slicer.vtkMRMLMarkupsNode.PointModifiedEvent,lambda c,e:self.schedule()),
                                  node.AddObserver(slicer.vtkMRMLMarkupsNode.PointRemovedEvent,lambda c,e:self.schedule())]
        return self.nodes[name]

    def schedule(self):
        if not self.busy: self.timer.start()

    def points(self,name):
        node=self.node(name); result={}
        for i in range(node.GetNumberOfControlPoints()):
            if node.GetNthControlPointPositionStatus(i)!=slicer.vtkMRMLMarkupsNode.PositionDefined: continue
            pos=[0.,0.,0.]; node.GetNthControlPointPositionWorld(i,pos)
            label=node.GetNthControlPointLabel(i)
            if label in result: raise ValueError('Landmark duplicado: '+label)
            result[label]=pos
        return result

    def volumeChanged(self,name,node):
        # A changed image invalidates its landmarks and scale; do not reuse silently.
        if self.nodes.get(name) and self.nodes[name].GetNumberOfControlPoints():
            self.nodes[name].RemoveAllControlPoints()
        self.settings[name].update(mm_per_unit=None,calibration_source=None,horizontal_confirmed=False)
        self.calibrationLengths.pop(name,None)
        self.confirmedOrientations.pop(name,None)
        self.result=None
        if name==self.name(): self.switchProjection()

    def switchProjection(self,*args):
        if self.busy: return
        self.stopPlacement(); name=self.name(); node=self.node(name)
        for n,m in self.nodes.items(): m.GetDisplayNode().SetVisibility(n==name)
        v=self.volumes[name].currentNode()
        if v:
            slicer.util.setSliceViewerLayers(background=v)
            matrix=__import__('vtk').vtkMatrix4x4(); v.GetIJKToRASMatrix(matrix)
            # Use the actual image plane (first two image axes), including oblique imports.
            normal=[matrix.GetElement(i,2) for i in range(3)]; transverse=[matrix.GetElement(i,0) for i in range(3)]
            center=[0.,0.,0.]
            bounds=[0.]*6; v.GetRASBounds(bounds); center=[(bounds[2*i]+bounds[2*i+1])/2 for i in range(3)]
            sn=slicer.app.layoutManager().sliceWidget('Red').mrmlSliceNode()
            sn.SetSliceToRASByNTP(*(normal+transverse+center+[0]))
            slicer.util.resetSliceViews()
        for control in (self.horizontal,self.posture): control.blockSignals(True)
        self.horizontal.setChecked(self.settings[name]['horizontal_confirmed'])
        self.posture.setCurrentIndex(self.posture.findText(self.settings[name]['posture']))
        for control in (self.horizontal,self.posture): control.blockSignals(False)
        s=self.settings[name]['mm_per_unit']; self.scaleLabel.setText('%.6g mm/unidad RAS'%s if s else 'Sin calibración validada')
        slicer.modules.markups.logic().SetActiveListID(node)
        self.updateNext(); self.calculate()

    def settingsChanged(self,*args):
        if self.horizontal.checked:
            points=self.points(self.name())
            if all(k in points for k in LABELS[:3]):
                self.confirmedOrientations[self.name()]=[list(points[k]) for k in LABELS[:3]]
            else:
                self.horizontal.setChecked(False)
        self.settings[self.name()]['horizontal_confirmed']=self.horizontal.checked
        self.settings[self.name()]['posture']=self.posture.currentText
        self.schedule()

    def updateNext(self):
        try:
            missing=[k for k in LABELS if k not in self.points(self.name())]
            self.nextLabel.setText('Siguiente: '+missing[0] if missing else 'Landmarks completos')
        except ValueError as e: self.nextLabel.setText(str(e))

    def placeNext(self):
        if not self.volumes[self.name()].currentNode():
            slicer.util.errorDisplay('Seleccione la radiografía de esta proyección'); return
        missing=[k for k in LABELS if k not in self.points(self.name())]
        if not missing: return
        self.calibrating=False; self.expected=missing[0]; self.startPlacement()

    def startPlacement(self):
        self.placing=True
        slicer.modules.markups.logic().SetActiveListID(self.node(self.name()))
        slicer.modules.markups.logic().StartPlaceMode(0)

    def stopPlacement(self,*args):
        self.placing=False; self.calibrating=False
        slicer.mrmlScene.GetNodeByID('vtkMRMLInteractionNodeSingleton').SetCurrentInteractionMode(slicer.vtkMRMLInteractionNode.ViewTransform)

    def pointAdded(self,name):
        if not self.placing or name!=self.name(): return
        node=self.node(name)
        idx=node.GetNumberOfControlPoints()-1
        node.SetNthControlPointLabel(idx,self.expected)
        node.SetNthControlPointDescription(idx,self.expected)
        self.placing=False
        if self.calibrating and self.expected=='CAL_A':
            self.expected='CAL_B'; qt.QTimer.singleShot(0,self.startPlacement)
        else:
            self.calibrating=False; self.updateNext(); self.schedule()

    def startCalibration(self):
        if not self.volumes[self.name()].currentNode():
            slicer.util.errorDisplay('Seleccione una radiografía'); return
        node=self.node(self.name())
        for i in reversed(range(node.GetNumberOfControlPoints())):
            if node.GetNthControlPointLabel(i) in ('CAL_A','CAL_B'): node.RemoveNthControlPoint(i)
        self.settings[self.name()].update(mm_per_unit=None,calibration_source=None)
        self.calibrating=True; self.expected='CAL_A'; self.startPlacement()

    def calibrate(self):
        try:
            p=self.points(self.name()); scale=manual_scale(p['CAL_A'],p['CAL_B'],self.length.value)
            self.settings[self.name()].update(mm_per_unit=scale,calibration_source='manual_reference')
            self.calibrationLengths[self.name()]=self.length.value
            self.scaleLabel.setText('%.6g mm/unidad RAS'%scale); self.calculate()
        except (KeyError,ValueError) as e: slicer.util.errorDisplay('Complete CAL_A/CAL_B: '+str(e))

    def confirmSpacing(self):
        if not self.volumes[self.name()].currentNode(): return
        if slicer.util.confirmYesNoDisplay('¿Verificó que la escala del volumen corresponde a mm anatómicos? PixelSpacing puede describir el detector y contener magnificación. Use marcador conocido si no está validada.'):
            self.settings[self.name()].update(mm_per_unit=1.,calibration_source='volume_spacing_user_verified')
            self.scaleLabel.setText('1 mm/unidad RAS, verificado por usuario'); self.calculate()

    def calculate(self):
        if self.busy: return
        projections={}; errors=[]
        for name in ('lat','flex','ext'):
            if not self.volumes[name].currentNode(): continue
            try:
                points=self.points(name)
                if not all(k in points for k in LABELS[:3]):
                    errors.append(name+': complete las 3 referencias de orientación'); continue
                orientation=[list(points[k]) for k in LABELS[:3]]
                if self.settings[name]['horizontal_confirmed'] and self.confirmedOrientations.get(name)!=orientation:
                    self.settings[name]['horizontal_confirmed']=False
                    if name==self.name():
                        self.horizontal.blockSignals(True); self.horizontal.setChecked(False); self.horizontal.blockSignals(False)
                volume=self.volumes[name].currentNode()
                if volume.GetImageData().GetDimensions()[2]!=1:
                    errors.append(name+': se requiere una radiografía 2D de un solo corte'); continue
                if self.settings[name]['calibration_source']=='manual_reference':
                    try:
                        self.settings[name]['mm_per_unit']=manual_scale(points['CAL_A'],points['CAL_B'],self.calibrationLengths[name])
                    except (ValueError,KeyError):
                        self.settings[name].update(mm_per_unit=None,calibration_source=None)
                projections[name]=Projection(points=world_to_anatomical(points),**self.settings[name])
            except (ValueError,KeyError,AttributeError) as e: errors.append(name+': '+str(e))
        self.result=study(projections)
        # Save world coordinates to permit round-trip restoration and recalibration.
        self.result['slicer_session']={name:{'world_points':self.points(name),'settings':dict(self.settings[name]),
                                           'volume_assignment_required_on_restore':True,'known_length_mm':self.calibrationLengths.get(name)} for name in projections}
        self.status.setText(' | '.join(errors) if errors else 'Resultados actualizados · pendientes de revisión')
        summary={name:{'global':r['global'],'segments':{k:{n:v for n,v in s.items() if n!='debug'} for k,s in r['segments'].items()},'qc':r['qc']} for name,r in self.result['projections'].items()}
        self.output.setPlainText(json.dumps({'projections':summary,'dynamic':self.result['dynamic']},indent=2,ensure_ascii=False,allow_nan=False))
        self.updateNext()

    def export(self):
        self.calculate()
        if not self.result['projections']: slicer.util.errorDisplay('Complete orientación y anatomía antes de exportar'); return
        path=qt.QFileDialog.getSaveFileName(slicer.util.mainWindow(),'Guardar estudio anónimo','','JSON (*.json)')
        if not path: return
        if not path.lower().endswith('.json'): path+='.json'
        try:
            figures={}
            for name in self.result['projections']:
                if self.result['projections'][name]['geometry']: figures[name]=svg(self.result,name)
            with open(path,'w',encoding='utf-8') as f: json.dump(self.result,f,indent=2,ensure_ascii=False,allow_nan=False)
            for name,content in figures.items():
                with open(os.path.splitext(path)[0]+'_'+name+'.svg','w',encoding='utf-8') as f: f.write(content)
            slicer.util.infoDisplay('JSON y figuras guardados. Sin identificadores DICOM ni imágenes de paciente.')
        except (OSError,ValueError) as e: slicer.util.errorDisplay(str(e))

    def restore(self):
        path=qt.QFileDialog.getOpenFileName(slicer.util.mainWindow(),'Restaurar JSON','','JSON (*.json)')
        if not path: return
        try:
            with open(path,encoding='utf-8') as f: data=json.load(f)
            if data.get('region')!='cervical' or data.get('schema_version')!='1.0': raise ValueError('Formato no compatible')
            session=data['slicer_session']
            # Validate before changing scene.
            for name,item in session.items():
                if name not in self.settings: raise ValueError('Proyección desconocida')
                Projection(points=world_to_anatomical(item['world_points']),**item['settings'])
            self.stopPlacement(); self.busy=True
            import vtk
            for name,item in session.items():
                node=self.node(name); node.RemoveAllControlPoints()
                for label,p in item['world_points'].items(): node.AddControlPoint(vtk.vtkVector3d(*p),label)
                self.settings[name]=dict(item['settings'])
                if self.settings[name]['horizontal_confirmed']: self.confirmedOrientations[name]=[list(item['world_points'][k]) for k in LABELS[:3]]
                if item.get('known_length_mm') is not None: self.calibrationLengths[name]=item['known_length_mm']
            self.busy=False; self.switchProjection()
            slicer.util.infoDisplay('Landmarks restaurados. Asigne radiografías antes de restaurar para evitar invalidar los puntos al cambiar de imagen. Verifique correspondencia y orientación.')
        except (OSError,ValueError,KeyError,TypeError) as e:
            self.busy=False; slicer.util.errorDisplay(str(e))

    def cleanup(self):
        self.timer.stop()
        for name,tags in self.observers.items():
            for tag in tags: self.nodes[name].RemoveObserver(tag)
