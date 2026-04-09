"""Curated, general-education snippets for RAG (not patient-specific). Sources are illustrative."""

MEDICAL_DOCUMENTS: list[dict[str, str]] = [
    {
        "text": (
            "Chest pain with shortness of breath, sweating, nausea, or pain radiating to the arm or jaw "
            "may indicate a serious cardiac event. Seek emergency care immediately."
        ),
        "source": "Mayo Clinic (chest pain — general)",
    },
    {
        "text": (
            "Stroke warning signs: face drooping, arm weakness, speech difficulty, sudden confusion, "
            "sudden severe headache, trouble walking. Call emergency services immediately."
        ),
        "source": "CDC (stroke signs)",
    },
    {
        "text": (
            "Common cold: runny nose, sore throat, mild cough. Rest, fluids, OTC symptom relief. "
            "See a clinician if high fever, breathing difficulty, or symptoms persist beyond ~10 days."
        ),
        "source": "CDC (common cold)",
    },
    {
        "text": (
            "Influenza (flu): fever, body aches, fatigue, cough. Antivirals may help if started early; "
            "seek care for breathing problems, confusion, or persistent high fever."
        ),
        "source": "CDC (flu overview)",
    },
    {
        "text": (
            "COVID-19 can cause fever, cough, loss of taste/smell, fatigue. "
            "Seek urgent care for trouble breathing, chest pain, confusion, or bluish lips."
        ),
        "source": "WHO/CDC (COVID-19 general)",
    },
    {
        "text": (
            "Hypertension is often defined as blood pressure at or above 130/80 mmHg. "
            "Very high readings (e.g., 180/120) especially with symptoms warrant urgent evaluation."
        ),
        "source": "AHA (blood pressure)",
    },
    {
        "text": (
            "Hypoglycemia (low blood sugar): shakiness, sweating, confusion. Treat per clinician plan; "
            "if severe or unconscious, seek emergency care."
        ),
        "source": "ADA (hypoglycemia — general)",
    },
    {
        "text": (
            "Hyperglycemia: thirst, frequent urination, fatigue. Very high glucose with vomiting or "
            "altered mental status may be an emergency (possible DKA/HHS)."
        ),
        "source": "ADA (hyperglycemia — general)",
    },
    {
        "text": (
            "Migraine: throbbing head pain, nausea, light sensitivity. "
            "Sudden worst-ever headache or headache with fever/neck stiffness needs urgent evaluation."
        ),
        "source": "NIH (headache/migraine — general)",
    },
    {
        "text": (
            "Tension headache: dull bilateral pressure. Usually benign; seek care if sudden severe onset "
            "or neurological symptoms."
        ),
        "source": "NIH (tension headache)",
    },
    {
        "text": (
            "Allergic reaction: hives, itching, swelling. "
            "Anaphylaxis (throat swelling, wheezing, faintness) is an emergency — use epinephrine if prescribed and call EMS."
        ),
        "source": "AAAAI (allergy/anaphylaxis — general)",
    },
    {
        "text": (
            "Asthma flare: wheeze, cough, chest tightness. "
            "Seek emergency care if peak flow drops severely, lips turn blue, or speech is difficult."
        ),
        "source": "ACAAI (asthma — general)",
    },
    {
        "text": (
            "Pneumonia: fever, cough with phlegm, shortness of breath, chest pain with breathing. "
            "Older adults may have subtle symptoms — lower threshold to seek care."
        ),
        "source": "ATS/CDC (pneumonia — general)",
    },
    {
        "text": (
            "Bronchitis: productive cough after a cold. Usually viral; see a clinician if high fever, "
            "blood in sputum, or prolonged symptoms."
        ),
        "source": "AAFP (bronchitis — general)",
    },
    {
        "text": (
            "Urinary tract infection: burning urination, frequency, urgency. "
            "Fever, flank pain, or vomiting may suggest kidney infection — seek prompt care."
        ),
        "source": "NIH (UTI — general)",
    },
    {
        "text": (
            "Kidney stones: severe flank pain, blood in urine, nausea. "
            "Severe pain, fever, or inability to urinate needs urgent care."
        ),
        "source": "NIH (kidney stones — general)",
    },
    {
        "text": (
            "Appendicitis: pain that migrates to right lower abdomen, nausea, fever. "
            "Worsening abdominal pain with fever warrants urgent evaluation."
        ),
        "source": "ACG (appendicitis — general)",
    },
    {
        "text": (
            "Gastroenteritis: vomiting, diarrhea, cramps. Hydration is key. "
            "Seek care for blood in stool, severe dehydration, or prolonged symptoms."
        ),
        "source": "CDC (gastroenteritis — general)",
    },
    {
        "text": (
            "GERD/acid reflux: heartburn, regurgitation. Lifestyle changes and OTC meds may help; "
            "red flags include difficulty swallowing or unintentional weight loss."
        ),
        "source": "ACG (GERD — general)",
    },
    {
        "text": (
            "Gallstones: right upper abdominal pain after fatty meals, nausea. "
            "Severe persistent pain, fever, or jaundice needs urgent evaluation."
        ),
        "source": "NIH (gallstones — general)",
    },
    {
        "text": (
            "Pancreatitis: severe upper abdominal pain radiating to back, nausea/vomiting. "
            "Often an emergency — seek immediate care."
        ),
        "source": "NIH (pancreatitis — general)",
    },
    {
        "text": (
            "Cellulitis: spreading red warm skin, fever. "
            "Facial involvement, rapidly spreading redness, or systemic symptoms need prompt care."
        ),
        "source": "AAD (cellulitis — general)",
    },
    {
        "text": (
            "Shingles: painful blistering rash in a band. Antivirals work best early; "
            "eye involvement or severe pain warrants urgent evaluation."
        ),
        "source": "CDC (shingles — general)",
    },
    {
        "text": (
            "Eczema flare: itchy dry patches. Seek care if widespread infection signs (pus, fever)."
        ),
        "source": "AAD (eczema — general)",
    },
    {
        "text": (
            "Conjunctivitis: red eye, discharge. Many cases viral; "
            "severe pain, vision changes, or contact lens wearer with pain needs urgent eye care."
        ),
        "source": "AAO (pink eye — general)",
    },
    {
        "text": (
            "Otitis media: ear pain, fever in children. "
            "Young infants with fever or severe ear pain should be evaluated promptly."
        ),
        "source": "AAP (ear infection — general)",
    },
    {
        "text": (
            "Sinusitis: facial pressure, nasal congestion, post-nasal drip. "
            "Seek care if high fever, severe headache, swelling around eyes, or symptoms >10 days worsening."
        ),
        "source": "AAFP (sinusitis — general)",
    },
    {
        "text": (
            "Strep throat: sore throat, fever, swollen nodes, sometimes no cough. "
            "Testing guides treatment; complications are uncommon but seek care if drooling or muffled voice."
        ),
        "source": "CDC (strep — general)",
    },
    {
        "text": (
            "Mononucleosis: fatigue, sore throat, swollen glands. "
            "Avoid contact sports due to spleen risk; seek care if severe dehydration or airway obstruction."
        ),
        "source": "CDC (mono — general)",
    },
    {
        "text": (
            "Dehydration: thirst, dry mouth, dizziness, dark urine. "
            "Infants, elders, and those with vomiting/diarrhea may need urgent rehydration."
        ),
        "source": "NIH (dehydration — general)",
    },
    {
        "text": (
            "Heat exhaustion: heavy sweating, weakness, cool skin, nausea. Move to cool place and hydrate; "
            "heat stroke (hot dry skin, confusion) is an emergency."
        ),
        "source": "CDC (heat illness — general)",
    },
    {
        "text": (
            "Hypothermia: shivering, confusion, slurred speech after cold exposure. "
            "Severe cases are emergencies — gradual rewarming and medical care."
        ),
        "source": "CDC (hypothermia — general)",
    },
    {
        "text": (
            "Panic attack: sudden fear, palpitations, chest tightness, tingling. "
            "First-time chest pain should be evaluated to rule out cardiac causes."
        ),
        "source": "ADAA (panic — general)",
    },
    {
        "text": (
            "Depression: low mood, loss of interest, sleep/appetite changes. "
            "If suicidal thoughts occur, seek immediate help (crisis line or emergency services)."
        ),
        "source": "NIMH (depression — general)",
    },
    {
        "text": (
            "Back strain: mechanical low back pain after lifting. "
            "Red flags: leg weakness, numbness in groin, bowel/bladder changes — emergency evaluation."
        ),
        "source": "AAOS (back pain — general)",
    },
    {
        "text": (
            "Sciatica: leg pain radiating from back along nerve path. "
            "Seek urgent care for progressive weakness or bowel/bladder dysfunction."
        ),
        "source": "AAOS (sciatica — general)",
    },
    {
        "text": (
            "DVT suspicion: calf swelling, warmth, pain after immobility or travel. "
            "Chest pain or shortness of breath with these signs may indicate PE — emergency care."
        ),
        "source": "ASH (DVT/PE — general)",
    },
    {
        "text": (
            "Anemia symptoms: fatigue, pallor, shortness of breath on exertion. "
            "Sudden severe shortness of breath or chest pain needs urgent care."
        ),
        "source": "NIH (anemia — general)",
    },
    {
        "text": (
            "Thyroid storm/hyperthyroid crisis: racing heart, fever, confusion — medical emergency."
        ),
        "source": "ATA (thyroid emergency — general)",
    },
    {
        "text": (
            "Hypothyroid: fatigue, cold intolerance, weight gain. Usually non-urgent evaluation; "
            "myxedema coma is rare and emergent."
        ),
        "source": "ATA (hypothyroid — general)",
    },
    {
        "text": (
            "Seizure: uncontrolled shaking, loss of consciousness. "
            "First seizure, prolonged seizure (>5 min), pregnancy, or injury warrants emergency care."
        ),
        "source": "Epilepsy Foundation (seizure — general)",
    },
    {
        "text": (
            "Meningitis concern: fever, stiff neck, severe headache, rash, confusion — emergency."
        ),
        "source": "CDC (meningitis — general)",
    },
    {
        "text": (
            "Vertigo (BPPV): brief spinning with head movement. "
            "New vertigo with neurological deficits or severe headache needs urgent evaluation."
        ),
        "source": "AAO-HNS (vertigo — general)",
    },
    {
        "text": (
            "Nosebleed: pinch soft nose, lean forward. "
            "Seek care if heavy bleeding, recurrent despite pressure, or after trauma."
        ),
        "source": "AAFP (epistaxis — general)",
    },
    {
        "text": (
            "Dental abscess: tooth pain, swelling, fever. "
            "Spreading facial swelling or trouble swallowing/breathing is urgent."
        ),
        "source": "ADA (dental infection — general)",
    },
    {
        "text": (
            "Burns: cool running water for minor burns. "
            "Large/deep burns, face/hand/genitals, or inhalation injury — emergency care."
        ),
        "source": "AAD (burns — general)",
    },
    {
        "text": (
            "Minor cuts: clean, pressure, bandage. "
            "Deep wounds, uncontrolled bleeding, or dirty wounds needing tetanus — seek care."
        ),
        "source": "CDC (wound care — general)",
    },
    {
        "text": (
            "Animal bite: wash wound; rabies risk depends on animal/region — seek medical advice promptly."
        ),
        "source": "CDC (animal bites — general)",
    },
    {
        "text": (
            "Tick bite: remove tick carefully; monitor for rash or fever (Lyme and other illnesses vary by region)."
        ),
        "source": "CDC (ticks — general)",
    },
    {
        "text": (
            "Pregnancy: vaginal bleeding, severe abdominal pain, severe headache, or decreased fetal movement "
            "warrant prompt obstetric evaluation."
        ),
        "source": "ACOG (pregnancy warning signs — general)",
    },
    {
        "text": (
            "Pediatric fever: infants under 3 months with fever need prompt medical evaluation."
        ),
        "source": "AAP (infant fever — general)",
    },
    {
        "text": (
            "Croup: barking cough in child; stridor at rest or retractions need urgent care."
        ),
        "source": "AAP (croup — general)",
    },
    {
        "text": (
            "Dehydration in children: fewer wet diapers, sunken eyes, lethargy — seek care promptly."
        ),
        "source": "AAP (pediatric dehydration — general)",
    },
    {
        "text": (
            "Food poisoning: nausea, vomiting, diarrhea hours after eating. "
            "Seek care for blood, high fever, severe dehydration, or neurologic symptoms."
        ),
        "source": "FDA (foodborne illness — general)",
    },
    {
        "text": (
            "Carbon monoxide: headache, nausea in poorly ventilated heated spaces — leave area and seek emergency care."
        ),
        "source": "CDC (CO poisoning — general)",
    },
    {
        "text": (
            "Poisoning/ingestion: contact poison control; unconscious, seizures, or breathing problems — call EMS."
        ),
        "source": "AAPCC (poisoning — general)",
    },
    {
        "text": (
            "Eye injury: chemical splash — flush with water and seek emergency eye care; "
            "penetrating injury — do not remove object; seek emergency care."
        ),
        "source": "AAO (eye injury — general)",
    },
    {
        "text": (
            "Testicular pain: sudden severe pain may be torsion — emergency urology evaluation."
        ),
        "source": "AUA (testicular torsion — general)",
    },
    {
        "text": (
            "Pelvic pain in women: ectopic pregnancy risk if pregnant or possible pregnancy — urgent evaluation."
        ),
        "source": "ACOG (pelvic pain — general)",
    },
    {
        "text": (
            "Rash with fever in child: some infections need urgent assessment; trust parental concern and seek care."
        ),
        "source": "AAP (rash + fever — general)",
    },
]
