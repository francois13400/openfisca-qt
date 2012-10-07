# -*- coding:utf-8 -*-
# Copyright © 2011 Clément Schaff, Mahdi Ben Jelloul

"""
openFisca, Logiciel libre de simulation de système socio-fiscal
Copyright © 2011 Clément Schaff, Mahdi Ben Jelloul

This file is part of openFisca.

    openFisca is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    openFisca is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with openFisca.  If not, see <http://www.gnu.org/licenses/>.
"""

from __future__ import division
from Config import CONF, VERSION
import pickle
from datetime import datetime


class Scenario(object):
    def __init__(self):
        super(Scenario, self).__init__()
        self.year = CONF.get('simulation', 'datesim').year
        self.indiv = {}
        # indiv est un dict de dict. La clé est le noi de l'individu
        # Exemple :
        # 0: {'quifoy': 'vous', 'noi': 0, 'quifam': 'parent 1', 'noipref': 0, 'noidec': 0, 
        #     'birth': datetime.date(1980, 1, 1), 'quimen': 'pref', 'noichef': 0}
        self.declar = {}
        
        # menage est un dict de dict la clé est la pref
        self.menage = {0:{'loyer':500,'so':3, 'code_postal':69001}}

        # on ajoute un individu, déclarant et chef de famille
        self.addIndiv(0, datetime(1975,1,1).date(), 'vous', 'chef')
    
    def check_consistency(self):
        '''
        Vérifie que le ménage entré est valide
        '''

        for noi, vals in self.indiv.iteritems():
            age = self.year - vals['birth'].year
            if age < 0:
                return u"L'année de naissance doit être antérieure à celle de la simulation (voir Fichier->Paramètres pour régler la date de la simulation"
            if vals['quifoy'] in ('vous', 'conj'):
                if age < 18: return u'Le déclarant et son éventuel conjoint doivent avoir plus de 18 ans'  # TODO
            else:
                if age > 25 and (vals['inv']==0): return u'Les personnes à charges doivent avoir moins de 25 ans si elles ne sont pas invalides'
#            if vals['quifoy'] == 'conj' and not vals['quifam'] == 'part':
#                return u"Un conjoint sur la déclaration d'impôt doit être le partenaire dans la famille"
        return ''
    
    def modify(self, noi, newQuifoy = None, newFoyer = None):
        oldFoyer, oldQuifoy = self.indiv[noi]['noidec'], self.indiv[noi]['quifoy']
        if newQuifoy == None: newQuifoy = oldQuifoy
        if newFoyer == None: newFoyer = oldFoyer
        if oldQuifoy == 'vous':
            toAssign = self.getIndiv(oldFoyer, 'noidec')
            del self.declar[oldFoyer]
            self._assignPerson(noi, quifoy = newQuifoy, foyer = newFoyer)
            for person in toAssign:
                oldPos = self.indiv[person]['quifoy']
                if oldPos == "vous": continue
                else: self.modify(person, newQuifoy = oldPos, newFoyer = 0)
        else:
            self._assignPerson(noi, quifoy = newQuifoy, foyer = newFoyer)
        self.genNbEnf()

    
    def hasConj(self, noidec):
        '''
        Renvoie True s'il y a un conjoint dans la déclaration 'noidec', sinon False
        '''
        for vals in self.indiv.itervalues():
            if (vals['noidec'] == noidec) and (vals['quifoy']=='conj'):
                return True
        return False
                
    def _assignVous(self, noi):
        ''' 
        Ajoute la personne numéro 'noi' et crée son foyer
        '''
        self.indiv[noi]['quifoy'] = 'vous'
        self.indiv[noi]['noidec'] = noi
        self.declar.update({noi:{}})

    def _assignConj(self, noi, noidec):
        ''' 
        Ajoute la personne numéro 'noi' à la déclaration numéro 'noidec' en tant 
        que 'conj' si declar n'a pas de conj. Sinon, cherche le premier foyer sans
        conjoint. Sinon, crée un nouveau foyer en tant que vous.
        '''
        decnum = noidec
        if (noidec not in self.declar) or self.hasConj(noidec):
            for k in self.declar:
                if not self.hasConj(k):
                    decnum = k
        if not self.hasConj(decnum):
            self.indiv[noi]['quifoy'] = 'conj'
            self.indiv[noi]['noidec'] = decnum
        else:
            self._assignVous(noi)

    def _assignPac(self, noi, noidec):
        ''' 
        Ajoute la personne numéro 'noi' à la déclaration numéro 'noidec' en tant 
        que 'pac'.
        '''
        self.indiv[noi]['quifoy'] = 'pac0'
        self.indiv[noi]['noidec'] = noidec

    
    def _assignPerson(self, noi, quifoy = None, foyer = None, quifam = None, famille = None):
        if quifoy is not None:
            if   quifoy     == 'vous': self._assignVous(noi)
            elif quifoy     == 'conj': self._assignConj(noi, foyer)
            elif quifoy[:3] == 'pac' : self._assignPac(noi, foyer)
        
        self.genNbEnf()

    def rmvIndiv(self, noi):
        oldFoyer, oldQuifoy = self.indiv[noi]['noidec'], self.indiv[noi]['quifoy']
        oldFamille, oldQuifam = self.indiv[noi]['noichef'], self.indiv[noi]['quifam']
        if oldQuifoy == 'vous':
            toAssign = self.getIndiv(oldFoyer, 'noidec')
            for person in toAssign:
                if self.indiv[person]['quifoy']     == 'conj': self._assignPerson(person, quifoy = 'conj', foyer = 0)
                if self.indiv[person]['quifoy'][:3] == 'pac' : self._assignPerson(person, quifoy = 'pac' , foyer = 0)
            del self.declar[noi]
        if oldQuifam == 'chef':
            toAssign = self.getIndiv(oldFamille, 'noichef')
            for person in toAssign:
                if self.indiv[person]['quifam']     == 'part': self._assignPerson(person, quifam = 'part', famille = 0)
                if self.indiv[person]['quifam'][:3] == 'enf' : self._assignPerson(person, quifam = 'enf' , famille = 0)
            del self.famille[noi]
        del self.indiv[noi]
        self.genNbEnf()

    def getIndiv(self, noi, champ = 'noidec'):
        for person, vals in self.indiv.iteritems():
            if vals[champ] == noi:
                yield person

    def addIndiv(self, noi, birth, quifoy, quifam):
        self.indiv.update({noi:{'birth':birth, 
                                'inv': 0,
                                'activite':0,
                                'quifoy': 'none',
                                'quifam': 'none',
                                'noidec':  0,
                                'noichef': 0,
                                'noipref': 0}})

        self._assignPerson(noi, quifoy = quifoy, foyer = 0, quifam = quifam, famille = 0)
        self.updateMen()

    def nbIndiv(self):
        return len(self.indiv)
            
    def genNbEnf(self):
        for noi, vals in self.indiv.iteritems():
            if vals.has_key('statmarit'):
                statmarit = vals['statmarit']
            else: statmarit = 2
            if self.hasConj(noi) and (noi == vals['noidec']) and not statmarit in (1,5):
                statmarit = 1
            elif not self.hasConj(noi) and (noi == vals['noidec']) and not statmarit in (2,3,4):
                statmarit = 2
            # si c'est un conjoint, même statmarit que 'vous'
            if vals['quifoy'] == 'conj':
                statmarit = self.indiv[vals['noidec']]['statmarit']
            vals.update({'statmarit':statmarit})
                
        for noidec, vals in self.declar.iteritems():
            vals.update(self.NbEnfFoy(noidec))

    def NbEnfFoy(self, noidec):
        out = {}
        n = 0
        for vals in self.indiv.itervalues():
            if (vals['noidec']==noidec) and (vals['quifoy'][:3]=='pac'):
                n += 1
                if (self.year - vals['birth'].year >= 18) and vals['inv'] == 0: out['nbJ'] += 1
                vals['quifoy'] = 'pac%d' % n
        return out
        pass

    def updateMen(self):
        '''
        Il faut virer cela
        '''
        people = self.indiv
        for noi in xrange(self.nbIndiv()):
            if   noi == 0: quimen = 'pref'
            elif noi == 1: quimen = 'cref'
            else:  quimen = 'enf%d' % (noi-1)
            people[noi].update({'quimen': quimen,
                                'noipref': 0})

    def __repr__(self):
        outstr = "INDIV" + '\n'
        for key, val in self.indiv.iteritems():
            outstr += str(key) + str(val) + '\n'
        outstr += "DECLAR" + '\n'
        for key, val in self.declar.iteritems():
            outstr += str(key) + str(val) + '\n'
        outstr += "MENAGE" + '\n'
        for key, val in self.menage.iteritems():
            outstr += str(key) + str(val) + '\n'
        return outstr

    def saveFile(self, fileName):
        outputFile = open(fileName, 'wb')
        pickle.dump({'version': VERSION, 'indiv': self.indiv, 'declar': self.declar, 'menage': self.menage}, outputFile)
        outputFile.close()
    
    def openFile(self, fileName):
        inputFile = open(fileName, 'rb')
        S = pickle.load(inputFile)
        inputFile.close()
        self.indiv = S['indiv']
        self.declar = S['declar']
        self.menage = S['menage']
        
        
        
def populate_from_scenario(datatable, scenario):
    
    from pandas import DataFrame, concat
    import numpy as np

    
    NMEN = CONF.get('simulation', 'nmen')
    datatable.NMEN = NMEN
    
    datatable._nrows = datatable.NMEN*len(scenario.indiv)
    MAXREV =     datatable.NMEN = CONF.get('simulation', 'maxrev')
    datesim = datatable.datesim

    datatable.table = DataFrame()

    idmen = np.arange(60001, 60001 + NMEN)
    
    for noi, dct in scenario.indiv.iteritems():
        birth = dct['birth']
        age = datesim.year- birth.year
        agem = 12*(datesim.year- birth.year) + datesim.month - birth.month
        noidec = dct['noidec']
        quifoy = datatable.description.get_col('quifoy').enum[dct['quifoy']]
        
        country = CONF.get('simulation', 'country')
        if country == 'france':
            quifam = datatable.description.get_col('quifam').enum[dct['quifam']]
            noichef = dct['noichef']
        
        quimen = datatable.description.get_col('quimen').enum[dct['quimen']]
        if country == 'france':
            dct = {'noi': noi*np.ones(NMEN),
                   'age': age*np.ones(NMEN),
                   'agem': agem*np.ones(NMEN),
                   'quimen': quimen*np.ones(NMEN),
                   'quifoy': quifoy*np.ones(NMEN),
                   'quifam': quifam*np.ones(NMEN),
                   'idmen': idmen,
                   'idfoy': idmen*100 + noidec,
                   'idfam': idmen*100 + noichef}
        else:
            dct = {'noi': noi*np.ones(NMEN),
                   'age': age*np.ones(NMEN),
                   'agem': agem*np.ones(NMEN),
                   'quimen': quimen*np.ones(NMEN),
                   'quifoy': quifoy*np.ones(NMEN),
                   'idmen': idmen,
                   'idfoy': idmen*100 + noidec}
            
        datatable.table = concat([datatable.table, DataFrame(dct)], ignore_index = True)

    country = CONF.get('simulation', 'country')
    if country == 'france':
        INDEX = ['men', 'fam', 'foy']
    elif country == 'tunisia':
        INDEX = ['men', 'foy']

    datatable.gen_index(INDEX)

    for name in datatable.col_names:
        if not name in datatable.table:
            datatable.table[name] = datatable.description.get_col(name)._default
        
    index = datatable.index['men']
    nb = index['nb']
    for noi, dct in scenario.indiv.iteritems():
        for var, val in dct.iteritems():
            if var in ('birth', 'noipref', 'noidec', 'noichef', 'quifoy', 'quimen', 'quifam'): continue
            if not index[noi] is None:
                datatable.set_value(var, np.ones(nb)*val, index, noi)

    index = datatable.index['foy']
    nb = index['nb']
    for noi, dct in scenario.declar.iteritems():
        for var, val in dct.iteritems():
            if not index[noi] is None:
                datatable.set_value(var, np.ones(nb)*val, index, noi)

    index = datatable.index['men']
    nb = index['nb']
    for noi, dct in scenario.menage.iteritems():
        for var, val in dct.iteritems():
            if not index[noi] is None:
                datatable.set_value(var, np.ones(nb)*val, index, noi)
        

    datatable.MAXREV = CONF.get('simulation', 'maxrev')
    var = CONF.get('simulation', 'xaxis')
    print var
    if var in ['sal', 'cho', 'rst']:
        datatable.XAXIS =  var + 'i'
    else:
        datatable.XAXIS =  'sali'
        
    if NMEN>1:
        var = datatable.XAXIS
        vls = np.linspace(0, MAXREV, NMEN)
        datatable.set_value(var, vls, {0:{'idxIndi': index[0]['idxIndi'], 'idxUnit': index[0]['idxIndi']}})

    datatable._isPopulated = True


XAXES = {}
XAXES['sal'] = ( [u'Salaire super brut',
                  u'Salaire brut',
                  u'Salaire imposable',
                  u'Salaire net'],  2 , 'sali')
XAXES['cho'] = ( [u'Chômage brut',
                  u'Chômage imposable',
                  u'Chômage net'], 1, 'choi')
XAXES['rst'] = ([u'Retraite brut',
                 u'Retraite imposable',
                 u'Retraite nette'], 0, 'rsti')
XAXES['cap'] = ([u'Revenus du capital brut',
                 u'Revenus du capital net'], 0 )
 



REV_TYPE = {'superbrut' : ['superbrut'],
             'brut': ['salbrut'],
             'net'      : ['sali']}        

