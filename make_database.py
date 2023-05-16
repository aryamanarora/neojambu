from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Language, Lemma, Reference, Concept, Base
from typing import List

import os
import csv
from tqdm import tqdm
from collections import defaultdict

colors = {
    "OIA": "E2DFD2",
    "MIA": "FFDEAD",
    "Pashai": "FFD6F6",
    "Chitrali": "FFACEF",
    "Shinaic": "FF81E6",
    "Kohistani": "FF25D5",
    "Kashmiric": "FF00CD",
    "Kunar": "ff68e0",
    "Western Pahari": "B94E16",
    "Central Pahari": "9E521B",
    "Eastern Pahari": "79421B",
    "Lahndic": "a4d6f5",
    "Punjabic": "7164FF",
    "Sindhic": "0066FF",
    "Gujaratic": "00CF4A",
    "Rajasthanic": "6BCD00",
    "Bhil": "09AD02",
    "Khandeshi": "2FFF2F",
    "Marathi-Konkani": "D50000",
    "Halbic": "AB8900",
    "Insular": "AC0000",
    "Eastern": "FFDE54",
    "Bihari": "FFCD00",
    "Eastern Hindi": "FF9A54",
    "Western Hindi": "FF6600",
    "Migratory": "63666A",
    "Nuristani": "9132a8",
    "Brahui": "49796B",
    "Old Dravidian": "679267",
    "South Dravidian I": "74C365",
    "South Dravidian II": "98FB98",
    "Central Dravidian": "29AB87",
    "North Dravidian": "4B6F44",
    "Munda": "00ffd0",
    "Burushaski": "f3ff05",
    "Nihali": "ff9a00",
    "Other": "FAF9F6",
}
order = list(colors.keys())

def parse_ref(ref: str) -> List[str]:
    """parses references of the forms 'ref1:page1;ref2:page2' with pages being optional"""
    if ref == '':
        return []
    return list(set([r.split(':')[0] for r in ref.split(';')]))

def main():
    # create engine and session
    if os.path.exists('data.db'):
        os.remove('data.db')
    engine = create_engine('sqlite:///data.db')
    Session = sessionmaker(bind=engine)
    session = Session()

    # create all tables
    Base.metadata.create_all(engine)

    # languages
    clades = {}
    with open('../data/cldf/languages.csv', 'r') as f:
        reader = csv.DictReader(f)
        for row in tqdm(reader, total=reader.line_num):
            language = Language(
                id=row['ID'],
                name=row['Name'],
                glottocode=row['Glottocode'],
                long=row['Longitude'],
                lat=row['Latitude'],
                clade=row['Clade'],
                color=colors[row['Clade']],
                order=order.index(row['Clade'])
            )
            clades[row['ID']] = row['Clade']
            session.add(language)

    # parameters
    params = {}
    with open('../data/cldf/parameters.csv', 'r') as f:
        reader = csv.DictReader(f)
        for row in tqdm(reader, total=reader.line_num):
            iden = 'src_' + row['ID']
            parameter = Lemma(
                id=iden,
                word=row['Name'],
                gloss=row['Description'],
                language_id=row['Language_ID'],
                notes=row['Etyma']
            )
            params[iden] = parameter
            session.add(parameter)

    # lemmata
    lemma_cts = defaultdict(int)
    param_clades = defaultdict(set)
    with open('../data/cldf/forms.csv', 'r') as f:
        reader = csv.DictReader(f)
        for row in tqdm(reader, total=reader.line_num):
            row['Parameter_ID'] = 'src_' + row['Parameter_ID']
            lemma = Lemma(
                id=row['ID'],
                word=row['Form'],
                gloss=row['Gloss'],
                native=row['Native'],
                phonemic=row['Phonemic'],
                original=row['Original'],
                notes=row['Description'],
                language_id=row['Language_ID'],
                origin_lemma_id=row['Parameter_ID'],
                relation="inheritance"
            )

            # language ct
            lemma_cts[row['Language_ID']] += 1

            # clade
            param_clades[row['Parameter_ID']].add(clades[row['Language_ID']])

            # add refs
            for ref in parse_ref(row['Source']):
                reference = session.query(Reference).filter_by(id=ref).first()
                if reference is None:
                    reference = Reference(id=ref)
                    session.add(reference)
                lemma.references.append(reference)

            session.add(lemma)

    # update language lemma counts
    for language_id, ct in lemma_cts.items():
        language = session.query(Language).filter_by(id=language_id).first()
        language.lemma_count = ct
    
    for param_id, clades in param_clades.items():
        lemma = params[param_id]
        lemma.clades = ','.join(list(clades))

    session.commit()

if __name__ == "__main__":
    main()