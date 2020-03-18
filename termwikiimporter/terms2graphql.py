# -*- coding: utf-8 -*-
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this file. If not, see <http://www.gnu.org/licenses/>.
#
#   Copyright © 2016-2019 The University of Tromsø
#   http://giellatekno.uit.no & http://divvun.no
#
"""Convert term dump to graphql."""

from termwikiimporter import bot, read_termwiki

# Read categories from dump
# Save categories, take care of ids
# Read terms from dump
# For each concept, save lemma (lang, expression, pos), get the id
# Save the concept, use connect for the lemmas and the category

categories = [
    'Beaivválaš giella‎', 'Boazodoallu',
    [
        'Boazonamahusat‎',
        ['Čoarvenamahusat‎'],
    ], 'Dihtorteknologiija ja diehtoteknihkka‎',
    [
        'Dihtorsánit‎',
        'Gulahallanrustegat‎',
        'Gulahallanrusttegat‎',
        'Ráhkkanusat‎',
    ], 'Dáidda ja girjjálašvuohta‎', 'Eanandoallu‎', 'Education‎',
    'Ekologiija ja biras‎', 'Ekonomiija ja gávppašeapmi‎', 'Geografiija‎',
    ['Báikenamat‎', 'Riikkanamat‎', 'riikkavulošvuohta‎'], 'Gielladieđa‎',
    ['Giellateknologiija‎'], 'Gulahallanteknihkka‎', 'Guolástus‎',
    'Huksenteknihkka‎', 'Juridihkka‎', 'Luonddudieđa ja matematihkka‎',
    [
        'Algebra‎', 'Anatomy‎', 'Ealibat‎',
        [
            'Gnagere – hamster‎', 'Gnagere – mus‎', 'Guollešlájat‎',
            [
                'Abbor', 'breiflabb‎'
                'brugde‎', 'flyndre‎', 'gjedde‎', 'havål‎', 'håbrann‎',
                'håkjerring‎', 'karpe‎', 'laks‎', 'lodde‎', 'makrell',
                'pigghå‎', 'rognkjeks‎', 'sil‎', 'sild‎', 'skate‎',
                'steinbit‎', 'stingsild‎', 'tangsprell‎', 'torsk‎', 'uer‎',
                'ulke‎', 'ål'
            ], 'Haredyr‎', 'Hvaler‎', 'Klovdyr',
            'Lađasjuolggat‎' ['Divrrit‎', [
                'Biller‎', 'Lopper‎', 'Lus', 'Nebbmunner‎', 'Nettvinger‎',
                'Rettvinger‎', 'Sommerfugler‎', 'Spretthaler‎', 'Steinfluer‎',
                'Tovinger‎', 'Vepser‎', 'Vårfluer‎', 'Øyenstikkere‎'
            ], 'Echinodermata‎', 'Heavnnit', [
                'Edderkopper',
                'Flått‎',
                'Kakerlakker‎',
                'Tusenbein‎',
                'Vevkjerringer‎',
            ], 'Hoppekreps‎', 'Jorbamáđut‎', 'Koralldyr', 'Lađasmáđut‎',
                              'Reabbaeallit‎', [
                                  'Bladfotkreps‎', 'Calanioida‎', 'Isopoder‎',
                                  'Rur‎', 'Tanglopper‎'
                              ], ], 'Loddešlájat‎',
            [
                'albatross‎', 'alke‎', 'and‎', 'avosett‎', 'bieter‎',
                'brakksvale‎', 'buskspurv‎', 'due‎', 'dykker‎', 'erle‎',
                'fasan‎', 'fink‎', 'fiskeørn‎', 'flamingo‎', 'fluesnapper‎',
                'fossekall‎', 'gjerdesmett‎', 'gjøk‎', 'hauk‎', 'hegre',
                'hærfugl', 'ibis‎', 'isfugl‎', 'jo', 'kardinal‎', 'kråke‎',
                'lerke‎', 'lo‎', 'lom‎', 'meis‎', 'måke‎', 'nattravn‎',
                'parula‎', 'pelikan‎', 'pirol‎', 'Regulidae‎', 'rikse‎',
                'råke‎', 'sandhøns‎', 'sanger‎', 'seiler‎', 'sidensvans‎',
                'skarv‎', 'skogshøns‎', 'snipe‎', 'spett‎', 'spettmeis‎',
                'spurv‎', 'stork‎', 'stormfugl‎', 'stormsvale‎', 'stær‎',
                'sule‎', 'svale‎', 'terne‎', 'tjeld‎', 'trane‎', 'trappe‎',
                'trekryper‎', 'triel‎', 'trost‎', 'trupial‎', 'ugle‎',
                'varsler‎', 'Vireoidae‎'
            ], 'moser‎', 'Njiččehasat‎',
            [
                'Flaggermus‎', 'Gnagere', ['Gnagere – bever‎'],
                'Gnagere – ekorn‎', 'Klovdyr‎', 'Klovdyr – kveg‎',
                'Klovdyr – svin‎', 'Piggsvindyr‎', 'Rovpattedyr – katt‎'
            ], 'Rovpattedyr‎', 'Rovpattedyr - hund‎', 'Rovpattedyr – bjørn‎',
            'Rovpattedyr – hund‎', 'Spissmusdyr‎', 'Tifotkreps‎',
            'Šlieddaeallit‎',
            [
                'Maxillopoda‎', 'Skjell/Bivalvia – Cartidoida‎',
                'Skjell/Bivalvia – Myoida‎', 'Skjell/Bivalvia – Mytiloida‎',
                'Skjell/Bivalvia – Pectinoida‎'
                'Skjell/Bivalvia – Veneroida‎', 'Skjell/Bivalvia –Ostroida‎',
                'Snegler/Gastropoda‎', 'Snegler/Gastropoda – Buccinoidea‎',
                'Snegler/Gastropoda – Littorinoidea‎',
                'Snegler/Gastropoda – Muricoidea‎',
                'Snegler/Gastropoda – Patelloidea‎'
            ]
        ], 'Geologiija', 'Geometriija‎', 'Universum‎', 'Šattut‎',
        [
            'amarant‎', 'Andreaeaceae‎', 'asparges‎', 'Athyriaceae‎',
            'beahcešattut', 'beallemasšattut‎', 'bergknapp‎'
            'bjørk‎', 'bjørnebrodd‎', 'bjørnekam‎', 'blåfjær‎', 'blærerot‎',
            'boskašattut (MS)', 'brasmegras‎', 'brasmegras – njuovvešattut‎',
            'brudelys‎', 'brunrot‎', 'bukkeblad‎', 'bulljelastat (MS)', 'bøk',
            'Chromista‎',
            [
                'brunalger – Phaeophysaea‎', 'gulgrønnalger – Xanthophyceae‎',
                'gullalger – Chrysophyceae‎', 'gullalger – Synurophyceae‎',
                'kiselalger – Bacillariophyta‎',
                'svelgflagellater – Cryptophyta‎'
            ], 'Cystopteridaceae‎', 'daŋasšattut (MS)', 'diehppelieđat (MS)',
            'dunkjevle‎', 'dvergjamne‎', 'einstape‎', 'erteblomst‎',
            'evjeblom‎', 'fiol‎', 'fjellflokk‎', 'fjellpryd‎', 'froskebitt‎',
            'furu‎', 'giftlilje‎', 'giilošattut‎', 'gjøglerblom‎',
            'gjøkesyre‎', 'gras‎', 'grønnalger – Chlorophyta‎'
            'Guobbarat‎', 'gáskálasšattut (MS)', 'hamp‎', 'havgras‎',
            'hengeving‎', 'hestespreng‎', 'hinnebeger‎', 'horbmášattut (MS)',
            'hornblad‎', 'Jeahkalat‎', 'jieretšattut (MS)',
            'juopmošattut (MS)', 'kaprifol‎', 'kattehale‎', 'kattost‎',
            'kildeurt‎', 'klokke‎', 'kornell‎', 'korsblomst‎',
            'kransalger – Charophyta‎', 'kråkefot‎', 'kurvplante‎',
            'leppeblomst‎', 'lilje‎', 'liljá (MS)', 'lin‎', 'lyng‎', 'løk‎',
            'lønn‎', 'maskeblomst‎', 'maure‎', 'mjølke‎', 'moskusurt‎',
            'muoškašattut (MS)', 'myrkongle‎', 'nartešattut‎', 'nellik‎',
            'nøkkerose‎', 'nøkleblom‎', 'oliventre‎', 'Onocleaceae‎',
            'orkide‎', 'orkidea/geapmanšattut (MS)', 'orkidé‎',
            'ormetunge‎', 'perikum‎', 'pors‎', 'Protozoa‎',
            ['øyealger – Euglenozoa‎'
             ], 'reatkašattut (MS)', 'reseda‎', 'rips‎', 'rome‎', 'rose‎',
            'rublad‎', 'ruvsošattut (MS)', 'ruvssošattut (MS)',
            'rødalger – Rhodophyta‎', 'sauløk‎', 'sildre‎', 'sisselrot‎',
            'siv‎', 'sivblom‎', 'skjermplante‎', 'slirekne‎', 'småburkne‎',
            'snelle‎', 'snylterot‎', 'soahkešattut (MS)', 'soldogg‎',
            'soleie‎', 'spolebusk‎', 'springfrø‎', 'starr‎', 'storburkne‎',
            'storkenebb‎', 'stortelg‎', 'sverdlilje‎', 'sypress‎',
            'sáhpalšattut (MS)', 'sølvbusk‎', 'søterot‎', 'søtvier‎',
            'tamarisk‎', 'tjernaks‎', 'trollhegg‎', 'tusenblad‎', 'tysbast‎',
            'valmue‎', 'vassgro‎', 'vier‎', 'vortemelk‎', 'ålegras‎'
        ]
    ], 'Medisiidna‎', ['Psychology‎'], 'Mášenteknihkka‎', 'Ođđa sánit‎',
    ['Davvisámegiela ođđa tearpmat‎',
     ['Ekonomiija‎', 'Minerálat‎']], 'Religion‎', 'Servodatdieđa‎',
    ['Social terms', ['Sexual minority terms‎']],
    'Stáda almmolaš hálddašeapmi‎', 'Teknihkka industriija duodji‎',
    'Álšateknihkka‎', 'Ásttoáigi ja faláštallan‎', 'Ávnnasindustriija‎'
]


def main():
    dump = bot.DumpHandler()
    find_categories(dump)


if __name__ == '__main__':
    main()