"""
Medical Dictionary — Phonetic + Levenshtein matching layer.

This is the core drug-correction intelligence. It runs on top of ANY ASR output
and corrects medical terms that get garbled (e.g. "I be proven" → "Ibuprofen").

Algorithm:
  1. Tokenise the raw transcript
  2. For each token (and 2-3 gram windows), compute:
     a. Exact match → no change
     b. Brand name match → map to generic
     c. Levenshtein distance ≤ threshold → correct
     d. Phonetic (soundex) match → correct
     e. Known mistranscription match → correct
  3. Return corrected transcript + list of corrections applied
"""

from __future__ import annotations
import re
import json
import unicodedata
from dataclasses import dataclass, field
from typing import Optional
import jellyfish  # soundex, metaphone, levenshtein


# ── Drug entries ─────────────────────────────────────────────────────────────

@dataclass
class DrugEntry:
    term: str
    term_type: str          # drug | dosage_unit | lab_test | procedure | condition
    phonetic: str
    mistranscriptions: list[str]
    brand_names: list[str]
    soundex: str = field(init=False)
    metaphone: str = field(init=False)

    def __post_init__(self):
        self.soundex = jellyfish.soundex(self.term.split()[0])
        self.metaphone = jellyfish.metaphone(self.term.split()[0])


# ── Full dictionary ───────────────────────────────────────────────────────────

RAW_DICTIONARY: list[dict] = [
    # ─── DRUGS ───────────────────────────────────────────────────────────────
    {"term": "Paracetamol", "type": "drug", "phonetic": "pa-ra-SEE-ta-mol",
     "mis": ["parasitamol","para see tamol","paris at a mall","para sita mole","parrot see tamale","para ceta mall"],
     "brands": ["Calpol","Dolo","Crocin","Tylenol","P-650","Febrinil","Dolopar"]},
    {"term": "Ibuprofen", "type": "drug", "phonetic": "eye-bew-PRO-fen",
     "mis": ["I be proven","ibu pro fan","I view profen","I proof in","eye brew pro fin","ibuprofen","ibu prof en"],
     "brands": ["Brufen","Combiflam","Advil","Ibugesic","Nurofen","Ibugesic Plus"]},
    {"term": "Tramadol", "type": "drug", "phonetic": "TRA-ma-dol",
     "mis": ["trauma doll","tram a doll","trauma dull","tramadole","drama doll","trama dol"],
     "brands": ["Ultracet","Contramal","Tramatas","Tramazac","Ultram"]},
    {"term": "Metformin", "type": "drug", "phonetic": "met-FOR-min",
     "mis": ["met for men","metaphor min","met forming","metform in","met forum in","metformine"],
     "brands": ["Glycomet","Glucophage","Obimet","Gluformin","Glucomet","Bigomet"]},
    {"term": "Glimepiride", "type": "drug", "phonetic": "glim-EP-i-ride",
     "mis": ["glimpse ride","glib pride","glam a pride","glimmer ride","glim pirate","glimpiride"],
     "brands": ["Amaryl","Glimstar","Glimy","Glimestar","Glimpid"]},
    {"term": "Warfarin", "type": "drug", "phonetic": "WAR-fa-rin",
     "mis": ["war for in","warfare in","war faring","wore far in","war far ring"],
     "brands": ["Coumadin","Warf","Sofarin","Warflo"]},
    {"term": "Clopidogrel", "type": "drug", "phonetic": "klo-PID-o-grel",
     "mis": ["close pedigree","clopidol grill","club piddle grill","clo pedigree","clopidol"],
     "brands": ["Plavix","Clopilet","Deplatt","Clopivas","Clopitab"]},
    {"term": "Enoxaparin", "type": "drug", "phonetic": "en-OX-a-pa-rin",
     "mis": ["e nox a parr in","enox a parent","in ox a paring","enoxa paren"],
     "brands": ["Clexane","Lovenox","Enox"]},
    {"term": "Aspirin", "type": "drug", "phonetic": "AS-pir-in",
     "mis": ["aspiring","a spring","as per in","aspren","asperin"],
     "brands": ["Ecosprin","Disprin","Loprin","Cardsprin"]},
    {"term": "Atorvastatin", "type": "drug", "phonetic": "a-TOR-va-sta-tin",
     "mis": ["a tour of statin","at or vast a tin","at over statin","ator vast a tin"],
     "brands": ["Atorva","Lipitor","Tonact","Storvas","Atorlip"]},
    {"term": "Omeprazole", "type": "drug", "phonetic": "oh-MEP-ra-zol",
     "mis": ["oh my prays all","home a prism","omega prazoal","oem pra zol","ome pra zol"],
     "brands": ["Omez","Prilosec","Ocid","Omecip"]},
    {"term": "Pantoprazole", "type": "drug", "phonetic": "pan-TOE-pra-zol",
     "mis": ["pant oh pray soul","panther prays all","panto prism","pan toe pra","pant o pra zol"],
     "brands": ["Pan 40","Pantocid","Nexpro","Pantop","Pantakind"]},
    {"term": "Amoxicillin", "type": "drug", "phonetic": "a-MOX-i-sil-in",
     "mis": ["a moxie see lin","amoks see lin","a mock silly in","a mox I sill in","amoxicilin"],
     "brands": ["Mox","Amoxil","Novamox","Moxylong","Wymox"]},
    {"term": "Azithromycin", "type": "drug", "phonetic": "a-ZITH-ro-my-sin",
     "mis": ["a with row my sin","az throw my sin","a zither oh my sin","as throw my sin","azithromycine"],
     "brands": ["Azithral","Zithromax","Azee","Azikem","Atm"]},
    {"term": "Telmisartan", "type": "drug", "phonetic": "tel-mi-SAR-tan",
     "mis": ["tell me sartan","tele me start on","telma sartan","tell me star tan"],
     "brands": ["Telma","Micardis","Telmikind","Sartel","Telmichek"]},
    {"term": "Amlodipine", "type": "drug", "phonetic": "am-LOD-i-peen",
     "mis": ["am loading peen","amlo di pine","a melody pin","am lo dip in","amlodipene"],
     "brands": ["Amlodac","Norvasc","Amlopress","Amlokind","Stamlo"]},
    {"term": "Metoprolol", "type": "drug", "phonetic": "me-TOE-pro-lol",
     "mis": ["metal oil","met oh pro lol","me toe pro loll","meta pro lol","metoprolo"],
     "brands": ["Metolar","Betaloc","Lopressor","Seloken","Met XL"]},
    {"term": "Ramipril", "type": "drug", "phonetic": "RAM-i-pril",
     "mis": ["ram a pill","ramp aril","rami prill","rummy prill"],
     "brands": ["Cardace","Ramistar","Ramace"]},
    {"term": "Escitalopram", "type": "drug", "phonetic": "es-si-TAL-o-pram",
     "mis": ["escape tell a pram","es sit a low pram","es cital o pram","essay tal o pram"],
     "brands": ["Nexito","Cipralex","Lexapro","S-Citadep","Stalopam"]},
    {"term": "Levothyroxine", "type": "drug", "phonetic": "lee-vo-thy-ROX-een",
     "mis": ["leave oh thy rocks in","levo thigh roxanne","levo thy rocks seen","levothyroxine"],
     "brands": ["Thyronorm","Eltroxin","Synthroid","Lethyrox","Thyrox"]},
    {"term": "Prednisolone", "type": "drug", "phonetic": "pred-NIS-o-lone",
     "mis": ["predator so lone","pred ni solo","prednisone alone","predniso lone"],
     "brands": ["Wysolone","Omnacortil","Deltacortril"]},
    {"term": "Methylprednisolone", "type": "drug", "phonetic": "meth-il-pred-NIS-o-lone",
     "mis": ["methyl predator so lone","metal prednisone","methyl prednisone"],
     "brands": ["Medrol","Solumedrol","Depo Medrol"]},
    {"term": "Furosemide", "type": "drug", "phonetic": "few-ROSE-a-mide",
     "mis": ["furious a maid","few rows a mid","furose might","furo semi day","frusemide"],
     "brands": ["Lasix","Frusenex","Uremide"]},
    {"term": "Spironolactone", "type": "drug", "phonetic": "spy-ro-no-LAK-tone",
     "mis": ["spiral lactone","spy rono lack tone","spy ro lactone"],
     "brands": ["Aldactone","Spirotone","Aldopar"]},
    {"term": "Insulin Glargine", "type": "drug", "phonetic": "IN-su-lin GLAR-jeen",
     "mis": ["insult in glarjeen","insulin glad gene","insulin glare jean","insulin glarjin"],
     "brands": ["Lantus","Basalog","Glaritus","Toujeo"]},
    {"term": "Insulin Aspart", "type": "drug", "phonetic": "IN-su-lin AS-part",
     "mis": ["insult in apart","insulin as part","insulate apart"],
     "brands": ["Novorapid","Fiasp","Novoact"]},
    {"term": "Cefuroxime", "type": "drug", "phonetic": "sef-yoo-ROX-eem",
     "mis": ["safe you rocks him","sef euro extreme","sef you rockseem"],
     "brands": ["Ceftum","Zinacef","Supacef"]},
    {"term": "Apixaban", "type": "drug", "phonetic": "a-PIX-a-ban",
     "mis": ["a picks a ban","apex a ban","a pixel ban","a pix abandon"],
     "brands": ["Eliquis","Apigat"]},
    {"term": "Rivaroxaban", "type": "drug", "phonetic": "ri-va-ROX-a-ban",
     "mis": ["riva rocks a ban","river ox a ban","riva rox ban"],
     "brands": ["Xarelto","Rivarox"]},
    {"term": "Dabigatran", "type": "drug", "phonetic": "da-BIG-a-tran",
     "mis": ["da big a tran","da biga tran","da big at ran"],
     "brands": ["Pradaxa","Dabigat"]},
    {"term": "Linagliptin", "type": "drug", "phonetic": "lin-a-GLIP-tin",
     "mis": ["linear glip tin","lina grip tin","lina glip ten"],
     "brands": ["Trajenta","Linage"]},
    {"term": "Sitagliptin", "type": "drug", "phonetic": "sit-a-GLIP-tin",
     "mis": ["sita glip tin","sit a grip tin","seater glip tin"],
     "brands": ["Januvia","Sitaglip","Sitamet"]},
    {"term": "Empagliflozin", "type": "drug", "phonetic": "em-pa-gli-FLOE-zin",
     "mis": ["empa gli flow zen","empty flow zin","empa glue floze in"],
     "brands": ["Jardiance","Empaglu"]},
    {"term": "Dapagliflozin", "type": "drug", "phonetic": "dap-a-gli-FLOE-zin",
     "mis": ["dapper flow zin","dapa gli flow zin","dapper glue floze"],
     "brands": ["Farxiga","Forxiga","Dapaglu"]},
    {"term": "Rosuvastatin", "type": "drug", "phonetic": "ro-SOO-va-sta-tin",
     "mis": ["rose of statin","row sue vast a tin","rosoo vast a tin"],
     "brands": ["Crestor","Rosuvas","Rosulip"]},
    {"term": "Gabapentin", "type": "drug", "phonetic": "gab-a-PEN-tin",
     "mis": ["grab a pen tin","gab upon tin","gaba pen ten"],
     "brands": ["Gabapin","Neurontin","Gabatop"]},
    {"term": "Pregabalin", "type": "drug", "phonetic": "preg-AB-a-lin",
     "mis": ["preg able in","pray gab a lin","preg ab a lin"],
     "brands": ["Lyrica","Pregab","Pregalin"]},
    {"term": "Labetalol", "type": "drug", "phonetic": "la-BET-a-lol",
     "mis": ["label all","la better lol","label a lol","la beta lol"],
     "brands": ["Lobet","Normodyne"]},
    {"term": "Hydroxychloroquine", "type": "drug", "phonetic": "hy-drox-ee-KLOR-o-kween",
     "mis": ["hydroxy chloroquine","hydroxy claw queen","hydroxy cloro queen"],
     "brands": ["HCQS","Plaquenil","HCQ"]},
    {"term": "Methotrexate", "type": "drug", "phonetic": "meth-oh-TREX-ate",
     "mis": ["metro tracks eight","method tracks ate","methyl tracks eight"],
     "brands": ["Folitrax","Imutrex"]},
    {"term": "Clonazepam", "type": "drug", "phonetic": "klo-NAZ-e-pam",
     "mis": ["clone a Z pam","clo naze a pam","clone as a pam","klonazepam"],
     "brands": ["Rivotril","Clonapax","Lonazep"]},
    {"term": "Alprazolam", "type": "drug", "phonetic": "al-PRAZ-o-lam",
     "mis": ["alpha pram","al praz oh lam","alpha proz a lam"],
     "brands": ["Xanax","Alprax","Restyl"]},
    {"term": "Levofloxacin", "type": "drug", "phonetic": "lee-vo-FLOX-a-sin",
     "mis": ["levo flox a sin","leave oh flocks a sin","levo flex a sin","levofloxa sin"],
     "brands": ["Levoflox","Levomac","Neoflox","Levaquin"]},
    {"term": "Ciprofloxacin", "type": "drug", "phonetic": "sip-ro-FLOX-a-sin",
     "mis": ["cipro flocks a sin","sip row flox a sin","see pro flox","ciprofloxa sin"],
     "brands": ["Ciplox","Cifran","Ciprobid"]},
    {"term": "Omeprazole", "type": "drug", "phonetic": "oh-MEP-ra-zol",
     "mis": ["oh my prays all","omega prays all"],
     "brands": ["Omez","Prilosec","Ocid"]},
    {"term": "Ondansetron", "type": "drug", "phonetic": "on-DAN-se-tron",
     "mis": ["on dance a tron","on dan se tron","on dan set ron"],
     "brands": ["Emeset","Ondam","Zofer","Vomikind"]},
    {"term": "Domperidone", "type": "drug", "phonetic": "dom-PER-i-done",
     "mis": ["dome perry done","dom per I done","dom period one"],
     "brands": ["Domstal","Motilium"]},
    {"term": "Clarithromycin", "type": "drug", "phonetic": "kla-RITH-ro-my-sin",
     "mis": ["clarity row my sin","cla rhythm ice in","clarity row mice in"],
     "brands": ["Klaricid","Claribid","Klacid"]},
    {"term": "Sertraline", "type": "drug", "phonetic": "SER-tra-leen",
     "mis": ["sir tree lean","sertra line","sir tra lean"],
     "brands": ["Zoloft","Serta","Daxid"]},
    {"term": "Amitriptyline", "type": "drug", "phonetic": "a-mee-TRIP-ti-leen",
     "mis": ["ami trip to lean","a meet triple lean","amee trip till lean"],
     "brands": ["Tryptomer","Amitop","Saroten"]},
    {"term": "Quetiapine", "type": "drug", "phonetic": "kwee-TY-a-peen",
     "mis": ["kwee tie a peen","queue tie a pin","kwee tia peen"],
     "brands": ["Seroquel","Qutan","Qutipin"]},
    {"term": "Olanzapine", "type": "drug", "phonetic": "oh-LAN-za-peen",
     "mis": ["oh lan za peen","o lanza peen","oh lance a peen"],
     "brands": ["Oleanz","Olimelt","Zyprexa"]},
    {"term": "Risperidone", "type": "drug", "phonetic": "ris-PER-i-done",
     "mis": ["ris perry done","risp eric done","ris per I done"],
     "brands": ["Sizodon","Rispond","Risnia","Risperdal"]},
    {"term": "Valproate", "type": "drug", "phonetic": "val-PRO-ate",
     "mis": ["val pro ate","val pro it","val prote"],
     "brands": ["Encorate","Depakote","Valparin","Epilim"]},
    {"term": "Levetiracetam", "type": "drug", "phonetic": "lee-ve-ty-RAS-e-tam",
     "mis": ["lee ve tire a sam","leve ti race a tam","leevee ti ras a tam"],
     "brands": ["Levera","Keppra"]},
    {"term": "Carbamazepine", "type": "drug", "phonetic": "kar-ba-MAZ-e-peen",
     "mis": ["car bam a zee peen","carba maze a peen","carba maz a pine"],
     "brands": ["Tegretol","Mazetol","Carbatol"]},
    {"term": "Bisoprolol", "type": "drug", "phonetic": "bis-OH-pro-lol",
     "mis": ["biz oh pro lol","bis o pro roll","biss oh pro lol"],
     "brands": ["Biselect","Bisocor","Zebeta"]},
    {"term": "Amiodarone", "type": "drug", "phonetic": "am-ee-OH-da-rone",
     "mis": ["ami oh da rone","amio drone","amy oh da ron"],
     "brands": ["Cordarone","Amiovast"]},
    {"term": "Digoxin", "type": "drug", "phonetic": "di-JOX-in",
     "mis": ["di jocks in","die jox in","di gox in","digoksin"],
     "brands": ["Lanoxin","Digox"]},
    {"term": "Allopurinol", "type": "drug", "phonetic": "al-oh-PYOOR-i-nol",
     "mis": ["alloy pure in all","allo pure in ol","allo poo rin ol"],
     "brands": ["Zyloric","Alloprin"]},
    {"term": "Colchicine", "type": "drug", "phonetic": "KOL-chi-seen",
     "mis": ["coal chi seen","cold chi scene","kolchi seen","colcicine"],
     "brands": ["Colchicap","Colchigen"]},
    {"term": "Folic Acid", "type": "drug", "phonetic": "FOH-lik AS-id",
     "mis": ["folio acid","folk acid","folic a sid"],
     "brands": ["Folvite","Folsafe","Folate"]},
    {"term": "Vitamin B12", "type": "drug", "phonetic": "VI-ta-min B twelve",
     "mis": ["vitamin be twelve","b12","vitamin bee 12","vit b 12"],
     "brands": ["Nervijen","Methylcobal","Cobalamin"]},
    {"term": "Vitamin D3", "type": "drug", "phonetic": "VI-ta-min D three",
     "mis": ["vitamin D3","vitamin dee 3","vit d three","cholecalciferol"],
     "brands": ["D-Rise","Calcirol","Arachitol"]},
    {"term": "Calcium Carbonate", "type": "drug", "phonetic": "KAL-see-um KAR-bo-nate",
     "mis": ["calcium carbon ate","cal see um carbon ate","calcium carb"],
     "brands": ["Shelcal","Calcimax","Caltrate"]},
    {"term": "Heparin", "type": "drug", "phonetic": "HEP-a-rin",
     "mis": ["hep a rin","hep rin","help a rin","hepper in"],
     "brands": ["Heparin","UFH"]},
    {"term": "Salbutamol", "type": "drug", "phonetic": "sal-BYOO-ta-mol",
     "mis": ["sal bew ta mole","sal boot a mol","sally bew ta mol"],
     "brands": ["Asthalin","Ventolin","Salbair"]},
    {"term": "Budesonide", "type": "drug", "phonetic": "byoo-DES-o-nide",
     "mis": ["bew dez oh nide","byoo deso nide","bew dessa nide"],
     "brands": ["Budecort","Pulmicort","Foracort"]},
    {"term": "Montelukast", "type": "drug", "phonetic": "mon-te-LOO-kast",
     "mis": ["monte luke cast","mont a look cast","month a look caste"],
     "brands": ["Montair","Singulair","Monti"]},
    {"term": "Dexamethasone", "type": "drug", "phonetic": "dex-a-METH-a-sone",
     "mis": ["dexa meth a sone","dex a meta zone","dexa meth a zone"],
     "brands": ["Dexona","Decadron"]},
    {"term": "Tacrolimus", "type": "drug", "phonetic": "ta-KRO-li-mus",
     "mis": ["ta crow lee mus","tack roll I mus","ta kro li mus"],
     "brands": ["Pangraf","Prograf"]},
    {"term": "Cetirizine", "type": "drug", "phonetic": "se-TIR-i-zeen",
     "mis": ["set a riz een","cet I rye zeen","settle rizeen"],
     "brands": ["Zyrtec","Alerid","Cetzine"]},
    {"term": "Fexofenadine", "type": "drug", "phonetic": "fex-oh-FEN-a-deen",
     "mis": ["fex oh fun a deen","fexy fen a dine","fexo fun a dean"],
     "brands": ["Allegra","Fexova"]},
    {"term": "Nitroglycerin", "type": "drug", "phonetic": "ny-tro-GLIS-er-in",
     "mis": ["nitro glee sir in","nitro glycerine","nitro glis a rin"],
     "brands": ["Nitrocine","Sorbitrate","GTN"]},
    {"term": "Nifedipine", "type": "drug", "phonetic": "ny-FED-i-peen",
     "mis": ["nifty pin","ni fed a peen","ni fe di pin"],
     "brands": ["Depin","Calcigard","Nicardia"]},
    {"term": "Losartan", "type": "drug", "phonetic": "lo-SAR-tan",
     "mis": ["low star tan","low sartan","lo sar tan"],
     "brands": ["Losar","Cozaar","Losacar","Repace"]},
    {"term": "Lisinopril", "type": "drug", "phonetic": "ly-SIN-o-pril",
     "mis": ["lie sin o pril","lye sino prill","li sino pill"],
     "brands": ["Listril","Prinivil","Zestril"]},
    {"term": "Enalapril", "type": "drug", "phonetic": "e-NAL-a-pril",
     "mis": ["e nala prill","en ala pril","E nal a pril"],
     "brands": ["Envas","Vasotec"]},
    {"term": "Donepezil", "type": "drug", "phonetic": "do-NEP-e-zil",
     "mis": ["done pezil","do nep a zil","done pe zil"],
     "brands": ["Aricept","Donecept","Alzil"]},
    {"term": "Memantine", "type": "drug", "phonetic": "me-MAN-teen",
     "mis": ["me man teen","mem an teen","me man tine"],
     "brands": ["Namenda","Admenta"]},
    {"term": "Sumatriptan", "type": "drug", "phonetic": "soo-ma-TRIP-tan",
     "mis": ["sue ma trip tan","suma trip tan","su ma trip ten"],
     "brands": ["Suminat","Imigran"]},
    {"term": "Topiramate", "type": "drug", "phonetic": "toe-PIR-a-mate",
     "mis": ["toe pear a mate","top I ra mate","to peer a mate"],
     "brands": ["Topmat","Topirol","Qudexy"]},
    {"term": "Tamsulosin", "type": "drug", "phonetic": "tam-SOO-lo-sin",
     "mis": ["tam sue lo sin","tam sue loo sin","tams u lo sin"],
     "brands": ["Urimax","Flomax","Tamsin"]},
    # ─── DOSAGE UNITS ─────────────────────────────────────────────────────
    {"term": "QDS", "type": "dosage_unit", "phonetic": "Q-D-S",
     "mis": ["cue d s","kudos","cuties","q d s","kew dee ess","qds"],
     "brands": []},
    {"term": "TDS", "type": "dosage_unit", "phonetic": "T-D-S",
     "mis": ["t d s","tedious","teddies","tea dee ess","tds","t.d.s"],
     "brands": []},
    {"term": "BD", "type": "dosage_unit", "phonetic": "B-D",
     "mis": ["be de","beady","buddy","b.d","bee dee","bd","bis in die"],
     "brands": []},
    {"term": "OD", "type": "dosage_unit", "phonetic": "O-D",
     "mis": ["oh dee","ode","oddy","o.d","once daily","od"],
     "brands": []},
    {"term": "PRN", "type": "dosage_unit", "phonetic": "P-R-N",
     "mis": ["pee are en","pirn","preen","p.r.n","prn","as needed"],
     "brands": []},
    {"term": "SOS", "type": "dosage_unit", "phonetic": "S-O-S",
     "mis": ["sos","sauce","s.o.s","if required","sos"],
     "brands": []},
    {"term": "STAT", "type": "dosage_unit", "phonetic": "STAT",
     "mis": ["state","start","stat","immediately","statt","stat dose"],
     "brands": []},
    {"term": "HS", "type": "dosage_unit", "phonetic": "H-S",
     "mis": ["aitch es","hes","his","h.s","at bedtime","hora somni"],
     "brands": []},
    # ─── LAB TESTS ────────────────────────────────────────────────────────
    {"term": "Troponin", "type": "lab_test", "phonetic": "TRO-po-nin",
     "mis": ["trope on in","tropo nine","tropical nin","trophy nin","troponine"],
     "brands": []},
    {"term": "Creatinine", "type": "lab_test", "phonetic": "kree-AT-i-neen",
     "mis": ["creative nine","create a nine","cree atinine","creat I nine","creatine"],
     "brands": []},
    {"term": "HbA1c", "type": "lab_test", "phonetic": "H-B-A-one-C",
     "mis": ["hba one see","hab a one see","h b a 1 c","glycated hemoglobin","haemoglobin a1c","hba1c"],
     "brands": []},
    {"term": "PT-INR", "type": "lab_test", "phonetic": "P-T-I-N-R",
     "mis": ["pt inner","pity inner","petty in r","p t inr","prothrombin","pt inr"],
     "brands": []},
    {"term": "eGFR", "type": "lab_test", "phonetic": "E-G-F-R",
     "mis": ["e g f r","egfr","estimated gfr","glomerular filtration"],
     "brands": []},
    {"term": "CBC", "type": "lab_test", "phonetic": "C-B-C",
     "mis": ["c b c","cbc","complete blood count"],
     "brands": []},
    {"term": "LFT", "type": "lab_test", "phonetic": "L-F-T",
     "mis": ["l f t","lft","liver function test","liver function"],
     "brands": []},
    {"term": "RFT", "type": "lab_test", "phonetic": "R-F-T",
     "mis": ["r f t","rft","renal function test","kidney function"],
     "brands": []},
    {"term": "ECG", "type": "lab_test", "phonetic": "E-C-G",
     "mis": ["e c g","ecg","electrocardiogram","ekg"],
     "brands": []},
    {"term": "ECHO", "type": "lab_test", "phonetic": "EK-oh",
     "mis": ["echo","echocardiogram","e k o","cardiac echo"],
     "brands": []},
    {"term": "TSH", "type": "lab_test", "phonetic": "T-S-H",
     "mis": ["t s h","tsh","thyroid stimulating hormone","thyroid test"],
     "brands": []},
    {"term": "D-Dimer", "type": "lab_test", "phonetic": "D-DY-mer",
     "mis": ["d dimer","dee dimer","d-dimer","dvt test"],
     "brands": []},
    {"term": "BNP", "type": "lab_test", "phonetic": "B-N-P",
     "mis": ["b n p","bnp","brain natriuretic peptide","heart failure marker"],
     "brands": []},
    {"term": "CRP", "type": "lab_test", "phonetic": "C-R-P",
     "mis": ["c r p","crp","c reactive protein","c-reactive protein"],
     "brands": []},
    {"term": "ESR", "type": "lab_test", "phonetic": "E-S-R",
     "mis": ["e s r","esr","erythrocyte sedimentation rate","sed rate"],
     "brands": []},
    {"term": "Procalcitonin", "type": "lab_test", "phonetic": "pro-kal-SY-to-nin",
     "mis": ["pro cal si to nin","pro calc I to nin","procalc a tonin"],
     "brands": []},
]


# ── Build lookup structures ───────────────────────────────────────────────────

def _build_entries() -> list[DrugEntry]:
    entries = []
    for item in RAW_DICTIONARY:
        e = DrugEntry(
            term=item["term"],
            term_type=item["type"],
            phonetic=item["phonetic"],
            mistranscriptions=item["mis"],
            brand_names=item["brands"],
        )
        entries.append(e)
    return entries


ENTRIES: list[DrugEntry] = _build_entries()

# Fast-lookup maps
EXACT_MAP: dict[str, str] = {}  # lowercase → canonical term
for e in ENTRIES:
    EXACT_MAP[e.term.lower()] = e.term
    for mis in e.mistranscriptions:
        EXACT_MAP[mis.lower()] = e.term
    for brand in e.brand_names:
        EXACT_MAP[brand.lower()] = e.term


# ── Correction dataclass ──────────────────────────────────────────────────────

@dataclass
class Correction:
    original: str
    corrected: str
    term_type: str
    method: str            # exact | brand | mistranscription | levenshtein | phonetic
    confidence: float


# ── Main correction function ──────────────────────────────────────────────────

def _normalise(text: str) -> str:
    """Lowercase, strip accents, collapse whitespace."""
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", text.strip().lower())


def _levenshtein_ratio(a: str, b: str) -> float:
    dist = jellyfish.levenshtein_distance(a, b)
    max_len = max(len(a), len(b), 1)
    return 1.0 - dist / max_len


def find_best_match(token: str, threshold: float = 0.75) -> Optional[tuple[str, str, float]]:
    """
    Try to match a single token (or short phrase) to a dictionary entry.
    Returns (canonical_term, term_type, confidence) or None.
    """
    norm = _normalise(token)

    # 1. Exact / mistranscription / brand match
    if norm in EXACT_MAP:
        canonical = EXACT_MAP[norm]
        entry = next(e for e in ENTRIES if e.term == canonical)
        method = "exact"
        if norm in [m.lower() for m in entry.mistranscriptions]:
            method = "mistranscription"
        elif norm in [b.lower() for b in entry.brand_names]:
            method = "brand"
        return canonical, entry.term_type, 1.0

    # 2. Levenshtein fuzzy match
    best_score = 0.0
    best_entry: Optional[DrugEntry] = None
    for entry in ENTRIES:
        score = _levenshtein_ratio(norm, entry.term.lower())
        if score > best_score:
            best_score = score
            best_entry = entry
        # Also check against mistranscriptions
        for mis in entry.mistranscriptions:
            s = _levenshtein_ratio(norm, mis.lower())
            if s > best_score:
                best_score = s
                best_entry = entry

    if best_score >= threshold and best_entry:
        return best_entry.term, best_entry.term_type, best_score

    # 3. Phonetic (soundex) match
    try:
        token_sdx = jellyfish.soundex(norm.split()[0])
        for entry in ENTRIES:
            if entry.soundex == token_sdx:
                return entry.term, entry.term_type, 0.70
    except Exception:
        pass

    return None


def correct_transcript(raw: str) -> tuple[str, list[Correction]]:
    """
    Main entry point. Takes raw ASR transcript, returns:
      - corrected transcript string
      - list of Correction objects describing each change
    """
    corrections: list[Correction] = []
    words = raw.split()
    result_tokens: list[str] = []
    i = 0

    while i < len(words):
        # Try 4-gram, 3-gram, 2-gram, 1-gram windows
        matched = False
        for n in [4, 3, 2, 1]:
            if i + n > len(words):
                continue
            phrase = " ".join(words[i:i+n])
            match = find_best_match(phrase)
            if match:
                canonical, term_type, confidence = match
                if confidence >= 0.75 or phrase.lower() in EXACT_MAP:
                    if canonical.lower() != phrase.lower():
                        corrections.append(Correction(
                            original=phrase,
                            corrected=canonical,
                            term_type=term_type,
                            method="match",
                            confidence=confidence,
                        ))
                    result_tokens.append(canonical)
                    i += n
                    matched = True
                    break
        if not matched:
            result_tokens.append(words[i])
            i += 1

    corrected = " ".join(result_tokens)
    return corrected, corrections


def get_drug_names() -> list[str]:
    """Return all canonical drug terms (for use in MTA computation)."""
    return [e.term for e in ENTRIES if e.term_type == "drug"]


def get_all_terms() -> list[str]:
    return [e.term for e in ENTRIES]
