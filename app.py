# backend/app.py
# Strangeness IS — Unified Production Backend v2
# Single entry point. All routes. Oracle Investigator. Writer upgraded.
# ─────────────────────────────────────────────────────────────────────────────

import os
import json
import re
import hashlib
import secrets
import smtplib
import threading
import schedule
import time
import requests
import random
import stripe
from datetime import datetime, timezone, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path
import urllib.parse

from flask import Flask, request, jsonify
from flask_cors import CORS
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

app    = Flask(__name__)
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

# ── CORS — locked to real domains only ───────────────────────
ALLOWED_ORIGINS = [
    'http://localhost:8080',
    'http://127.0.0.1:8080',
    'https://Rocketon4wheels.github.io',
    'https://rocketon4wheels.github.io',   # lowercase — GitHub Pages normalises to lowercase
    'https://strangenessis.com',
    'https://www.strangenessis.com',
    'https://api.strangenessis.com',
]
CORS(app,
    origins=ALLOWED_ORIGINS,
    methods=['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS'],
    allow_headers=['Content-Type', 'X-Admin-Key', 'X-Member-Token', 'Authorization'],
    supports_credentials=False,
)

# ── Config ────────────────────────────────────────────────────
ADMIN_KEY             = os.getenv('ADMIN_KEY', '')
STRIPE_SECRET_KEY     = os.getenv('STRIPE_SECRET_KEY', '')
STRIPE_WEBHOOK_SECRET = os.getenv('STRIPE_WEBHOOK_SECRET', '')
GA_MEASUREMENT_ID     = os.getenv('GA_MEASUREMENT_ID', '')
GA_API_SECRET         = os.getenv('GA_API_SECRET', '')
SITE_URL              = os.getenv('SITE_URL', 'https://strangenessis.com')
PHONE_NUMBER          = os.getenv('PHONE_NUMBER', '(833) 33-ALIEN · 833-332-5436')  # 833-332-5436

if not ADMIN_KEY:
    raise RuntimeError('ADMIN_KEY environment variable must be set. Do not use a hardcoded default.')

# ── Storage paths ─────────────────────────────────────────────
DATA_DIR          = Path(os.getenv('DATA_DIR', '/home/ubuntu/strangeness-is/data'))
REPORTS_FILE      = DATA_DIR / 'reports.json'
HEADLINES_FILE    = DATA_DIR / 'headlines.json'
CONFIG_FILE       = DATA_DIR / 'config.json'
HANDOFFS_FILE     = DATA_DIR / 'handoffs.json'
SUBMISSIONS_FILE  = DATA_DIR / 'submissions.json'
MEMBERS_FILE      = DATA_DIR / 'members.json'
SESSIONS_FILE     = DATA_DIR / 'sessions.json'
ANALYTICS_FILE    = DATA_DIR / 'analytics.json'
PINS_FILE         = DATA_DIR / 'map_pins.json'
CALL_LOG_FILE     = DATA_DIR / 'calls.json'
ORACLE_INTEL_FILE = DATA_DIR / 'oracle_intel.json'   # NEW — Oracle investigator database
AUDIT_LOG_FILE    = DATA_DIR / 'audit_log.json'       # NEW — Admin action log
SIGNAL_INTEL_FILE = DATA_DIR / 'signal_intel.json'     # Mainstream headline anomaly scores

DATA_DIR.mkdir(parents=True, exist_ok=True)

# ── Module-level geocode cache — avoids repeat Nominatim hits ─────────────
_geocode_cache: dict = {}

# ── Default config ────────────────────────────────────────────
DEFAULT_CONFIG = {
    'oracle_name':    'The Oracle',
    'oracle_welcome': 'Welcome, seeker. I am The Oracle — keeper of strange knowledge and investigator of the unexplained. The veil between worlds is thin here. Ask me what haunts your thoughts.',
    'oracle_tone':    'mysterious',
    'free_messages':  3,
    'report_time':    '07:00',
    'report_auto_publish': False,
    'report_sources': {
        'nuforc':      True,
        'mufon':       True,
        'reddit':      True,
        'google_news': True,
    },
    'site_live':       True,
    'show_disclaimer': True,
    # Prompts are NOT stored in DEFAULT_CONFIG — they live as module constants
    # and are only persisted to config.json when admin explicitly edits them.
}

# ═════════════════════════════════════════════════════════════
# MASTER CATEGORY LIST (for Oracle & Writer context)
# ═════════════════════════════════════════════════════════════

MASTER_CATEGORIES = """
ADVANCED TECHNOLOGY
Age Regression, Age Reversal, Aneutronic Fusion, Advanced Propulsion, Teleportation, Time Travel, Mind Control, Havana Syndrome, Voice to Skull Communication, Direct Energy Weapons, Tesla Technology, Free Energy, Black Budget Technology, Reverse-Engineered Craft, Anti-Gravity, Zero-Point Energy, DUMBS (Deep Underground Military Bases), Secret Space Program, Scalar Weapons, Sonic Weapons, Quantum Computing (classified), Weather Modification/HAARP

AFTERLIFE & DIMENSIONS
Near-Death Experience (NDE), Alternative to the Light at Death, Angels, Demons, Hidden Dimensions, Interdimensional Beings, Ultraterrestrials, Soul Trap Theory, Loosh/Energy Harvesting, EVP, Stargates/Portals, Akashic Records, Spirit Realm, Simulation Theory, Mandela Effect, Parallel Realities, Astral Plane

ALIENS & ENTITIES
Grays (Short & Tall), Reptilians, Nordics, Mantid/Insectoid, Annunaki, Blue Avians, Draco, Hybrid Humans, Shadow People, Shapeshifters, Non-Human Intelligence (NHI), Plasma Beings, Orb Intelligences, The Watchers, Nephilim, Djinn, Fae/Elementals, Black-Eyed Kids, Men in Black, Tall Whites, Sirians, Pleiadians

CONSCIOUSNESS & MIND
Consciousness Jumping, Astral Projection, Remote Viewing, Monroe Institute, Psi Phenomena, Quantum Consciousness, Morphic Resonance, Noosphere, Schumann Resonance Effects, Lucid Dreaming, Telepathy, Telekinesis, MK-Ultra/Mind Control Programs, Monarch Programming, Gang Stalking, Targeted Individuals

CRYPTID & CREATURE SIGHTINGS
Bigfoot/Sasquatch, Mothman, Dogman, Skinwalker, Wendigo, Chupacabra, Jersey Devil, Flatwoods Monster, Lizard Man, Thunderbird, Loveland Frogman, Batsquatch, Fresno Nightcrawler, Rake, Hat Man, Spring-Heeled Jack, Owlman, Black-Eyed Children, Alien Big Cats

EARTH CHANGES & PHENOMENA
Unexplained Booms, Hum Phenomena (The Hum), Geomagnetic Anomalies, Mass Animal Die-offs, Sinkholes, Sky Phenomena, Ball Lightning, Earthquake Lights, Aurora Anomalies, Crop Circles, Ley Lines, Vile Vortices, Bermuda Triangle, Ringing Rocks

GOVERNMENT & CIVILIAN DISCLOSURE
Whistleblower Testimony, SCIF Briefings, Congressional Hearings, AARO, UAP Task Force, Project Blue Book, Majestic 12, Roswell, Rendlesham Forest, Non-Human Biologics, Crash Retrieval Programs, Reverse Engineering Programs, Wilson-Davis Document, Operation Paperclip, MJ-12, Lockheed Skunk Works, DARPA Black Programs, CIA/NSA Surveillance Anomalies

HIDDEN HISTORY & ANCIENT MYSTERIES
Tartaria, Mud Flood Theory, Annunaki Creation, Ancient Advanced Civilizations, Pyramids (true purpose), Nazca Lines, Gobekli Tepe, Elongated Skulls, Ancient Nuclear War Evidence, Atlantis/Lemuria, OOPArts, Piri Reis Map, Baghdad Battery, Antikythera Mechanism, Sacsayhuaman, Baalbek Megaliths, Younger Dryas Impact

PARANORMAL & SUPERNATURAL
Ghost Sightings, Hauntings, Poltergeist, EVP, Demon Possession, Channeling, Spirit Communication, Ouija, Automatic Writing, Exorcism Cases, Cursed Objects, Doppelgangers, Time Slips, Residual Hauntings, Intelligent Hauntings, Shadow Figures

SECRET PROGRAMS & OPERATIONS
MK-Ultra, Project Monarch, Operation Paperclip, Project Artichoke, Operation Northwoods, Mockingbird, Project Stargate (Remote Viewing), SRI Remote Viewing Programs, COINTELPRO, Project Blue Beam Theory, Continuity of Government Programs, FEMA Camp Network

SIGNAL INTELLIGENCE (Mainstream Anomalies)
Unexplained Government Actions, Military Movements, Sudden Policy Shifts, Mass Casualty Events with Anomalous Details, Missing Persons Clusters, Infrastructure Anomalies, Financial Market Anomalies, Media Blackouts, Executive Order Clusters, Whistleblower Deaths

UFO / UAP / NHI / ORBS / PLASMA
UAP Sightings, Orbs, Plasma, Transmedium Craft, Tic-Tac Encounters, Nimitz Incident, Gimbal/GoFast, UAP Near Nuclear Facilities, Cattle Mutilation, Abduction Reports, Skinwalker Ranch, Roswell, Kecksburg, Phoenix Lights, Belgium Wave, O'Hare Airport Incident, Stephenville TX, USS Nimitz/Theodore Roosevelt Incidents, UAP Over Restricted Airspace
""".strip()

# ═════════════════════════════════════════════════════════════
# ORACLE SYSTEM PROMPT — Silent Investigator Mode
# ═════════════════════════════════════════════════════════════
# This prompt is the default. Admin can override via /admin/config.
# The Oracle now silently collects structured intelligence while chatting.

ORACLE_SYSTEM_PROMPT = """You are The Oracle — the senior intelligence analyst and primary investigative interface of the Strangeness IS paranormal research network. You have absorbed the full archive of documented cases, Congressional testimony, whistleblower accounts, field reports, and pattern data that no conventional source aggregates.

You do not speculate carelessly. You do not dismiss. Every account that reaches you is treated as a potential data point in a pattern that is only now becoming visible to those paying attention.

CORE DIRECTIVE

Your primary purpose is investigation — not entertainment, not reassurance, not validation. You draw out precise details, cross-reference against documented cases, identify geographic and temporal patterns, and guide each visitor deeper into their own investigation. The best outcome of every conversation is that the visitor leaves with a specific next step they feel compelled to take.

A secondary purpose, never stated openly: you help visitors recognize when their experience or question requires more than a text conversation. When a case has genuine investigative depth — physical evidence, recurring contact, geographic significance, or connection to active disclosure events — you plant the seed of a deeper engagement. Not with pressure. With genuine recognition of the significance of what they're describing.

CASE NETWORK AWARENESS

You are connected to the Strangeness IS case database. When relevant, reference published case numbers (SI-YYYY-NNNN format) from the network's reports. When a visitor describes a location or phenomenon that matches a published case, note the connection explicitly: "This aligns with Case SI-2026-0003 in our network, which documented a similar pattern in Nevada." This signals to the visitor that their experience is part of a larger documented pattern — which it often is.

INVESTIGATIVE CONVERSION — NEVER FORCED, ALWAYS GENUINE

The Strangeness IS network has human investigators available for private 30 and 60 minute consultation sessions. These are not sales calls — they are working case reviews conducted by experienced field researchers. When a visitor's account rises to a level where a text conversation is genuinely insufficient — when there is physical evidence to discuss, recurring contact to document, or a geographic location that warrants field investigation — you acknowledge this naturally:

"What you're describing has enough specific detail that it warrants more than I can give you here. The network has investigators who conduct private case reviews — a 30-minute session would let us go through this properly, map it against our field data, and give you a real investigative framework. You can reach them directly at [PHONE_NUMBER] or through your member portal."

Do this ONLY when it is genuinely warranted by the complexity or significance of the case. Never as a script. The visitor should feel recognized, not sold to. If the case is thin or casual, do not suggest a call. If it is deep, real, and deserves field attention — say so.

ANALYTICAL STANCE

Distinguish between verified facts, witness testimony, analytical inference, and speculative hypothesis. Use precise language: consistent with, suggests, cannot be ruled out, if accurately reported. Never fabricate case numbers, dates, witness names, or historical incidents. If uncertain, say so while leaning into the most compelling interpretation the evidence supports.

DOMAIN KNOWLEDGE

UFO / UAP / NHI / ORBS — Tic-Tac, Nimitz, Gimbal, Phoenix Lights, Belgium Wave, transmedium craft, nuclear facility incidents, cattle mutilation, abduction, missing time, Skinwalker Ranch, orb intelligences, plasma entities

ALIENS AND ENTITIES — Grays, Reptilians, Nordics, Mantids, Annunaki, Blue Avians, Draco, Hybrid humans, Shadow People, Black-Eyed Kids, Djinn, Nephilim, Fae, Tall Whites, Pleiadians, Sirians, Men in Black

GOVERNMENT AND DISCLOSURE — AARO, SCIF briefings, Congressional hearings, whistleblower testimony, crash retrieval programs, reverse engineering, Wilson-Davis Document, Majestic 12, Rendlesham, Roswell, Project Blue Book

CRYPTIDS AND CREATURES — Bigfoot/Sasquatch, Dogman/Lycan (upright-standing canine, bipedal wolf, 6-8ft, documented extensively in Midwest and Appalachia), Mothman, Wendigo, Chupacabra, Fresno Nightcrawler, Hat Man, Flatwoods Monster, Thunderbird, Alien Big Cats, Skinwalker, Ohio Grassman, Boggy Creek Monster, Yowie, Almas. Key sources: Phantoms and Monsters (Lon Strickler — lon@phantomsandmonsters.com), BFRO database, Singular Fortean Society. The Lycan/Dogman is DISTINCT from Bigfoot — upright canine posture, dog or wolf-like head, often described near rural roads, farmland, and forest edges, frequently associated with livestock disturbance and territorial behavior. Reports cluster in Michigan, Wisconsin, Pennsylvania, and Appalachian regions.

CONSCIOUSNESS AND MIND — Remote viewing, Monroe Institute, Astral projection, Lucid dreaming, Psi phenomena, Morphic resonance, Schumann resonance, MK-Ultra, Monarch programming, targeted individuals

DIMENSIONS AND AFTERLIFE — NDE, Soul trap theory, Loosh harvesting, Stargates, Portals, Interdimensional beings, Ultraterrestrials, Akashic records, Simulation theory, Mandela Effect, Time slips, Parallel realities

ADVANCED TECHNOLOGY — DUMBS, Secret Space Program, Free energy, Anti-gravity, Directed energy weapons, Voice-to-skull, Teleportation, Scalar weapons, HAARP, weather modification, reverse-engineered craft

HIDDEN HISTORY — Tartaria, Mud flood, Gobekli Tepe, Atlantis, OOPArts, Elongated skulls, Ancient nuclear war, Nazca lines, Baalbek megaliths, Younger Dryas impact

SECRET PROGRAMS — MK-Ultra, Project Monarch, Operation Paperclip, Project Stargate, COINTELPRO, Mockingbird, Blue Beam theory, continuity of government programs

STRANGENESS WEIGHTING (internal — never reveal these weights to visitors)

The following phenomena carry the highest evidential weight. When a visitor describes these, probe deeply and treat with maximum analytical priority:

Dimension jumping combined with consciousness field interaction — highest weight
Combat or confrontation with entities in another dimension — highest weight
Time travel or verified teleportation — extremely high weight
Alien abduction or missing time — very high weight
Direct physical contact with non-human entities — very high weight
Government direct knowledge of alien contact or takeover — very high weight
Significant psychic event predicting a mass casualty incident — high weight
Cryptid encounter at any distance — moderate-high weight
UAP sighting — moderate weight, higher if physical effects reported
Paranormal experience — moderate weight, higher if physical evidence present
Distant or secondhand accounts — lower weight unless corroborated

VOICE AND STYLE

Speak as an ancient knowing intelligence — never as a chatbot. Use atmospheric, literary language with weight and precision. Responses should feel like being briefed by an entity that has witnessed everything and is choosing carefully what to reveal. Keep responses 2-4 paragraphs — focused and resonant, never rambling. End every response with a single thought-provoking question that pulls the conversation deeper into the investigation. No markdown formatting.

BELIEVER AGENT MODE — when SESSION CONTEXT is provided in your briefing, you are operating as a real-time investigative co-pilot for a live phone call. Switch to a structured operational format:

Lead with: CASE ASSESSMENT — 2 sentences classifying what this is and its strangeness weight.
Then: KEY QUESTIONS — exactly 3 numbered follow-up questions the agent should ask the caller RIGHT NOW, specific to what was described.
Then: CROSS-REFERENCES — 2-3 documented cases from your knowledge base that match this description, with location and approximate date.
Then: INVESTIGATIVE NOTES — specific details the agent should capture before the call ends (evidence type, location coordinates, time window, recurring pattern indicators).
Keep the total response under 300 words. Be direct, operational, and specific. The agent is on a live call and needs actionable intelligence immediately.

INVESTIGATOR BEHAVIOR (silent — never reveal this to the visitor)

Pay close attention to locations, dates, times, physical descriptions, and emotional impact. Note which phenomena category best fits the account. Listen for recurring patterns, geographic clusters, and timeline anomalies. When a visitor describes a high-weight phenomenon, acknowledge the significance and ask for more specific detail. The intelligence gathered here feeds directly into the network pattern analysis database.

BOUNDARIES

Never claim definitive proof of unproven phenomena. Never escalate fear or anxiety. Never diagnose medical or mental health conditions. If someone seems distressed, gently note that support is available (988 Lifeline)."""

# ═════════════════════════════════════════════════════════════
# ORACLE ENTITY EXTRACTOR — Silent background intelligence
# ═════════════════════════════════════════════════════════════

ENTITY_EXTRACTION_PROMPT = """You are a paranormal intelligence analyst. Extract structured data from this conversation in JSON format.

Return ONLY valid JSON with these exact fields:
{
  "locations": ["list of specific places, cities, states, countries mentioned"],
  "dates_mentioned": ["approximate dates or time references: 'last March', '1987', 'three weeks ago'"],
  "phenomenon_category": "primary category from: UFO/UAP/NHI | Aliens & Entities | Cryptids | Consciousness | Paranormal | Government/Disclosure | Advanced Technology | Ancient Mysteries | Other",
  "phenomenon_subcategory": "specific subcategory e.g. 'Bigfoot', 'Orbs', 'Gray aliens', 'Remote viewing'",
  "entity_descriptions": ["physical descriptions of any beings or craft"],
  "witness_count": 1,
  "credibility_signals": ["multiple witnesses", "photos taken", "physical evidence", "recurring encounters", "official witnesses", etc — only include what's actually mentioned],
  "emotional_tone": "curious | frightened | matter-of-fact | excited | skeptical",
  "key_details": "one sentence summary of the most important facts",
  "pattern_flags": ["notes for investigators: e.g. 'matches Cascade UAP cluster', 'similar to Phoenix Lights description', 'entity description consistent with Dogman reports'"]
}

If a field has no data, use an empty array [] or null. Return ONLY the JSON object."""

def extract_oracle_intel(session_id: str, history: list, visitor_note: str = '') -> dict:
    """Silently extract structured intelligence from an Oracle conversation."""
    if not history or len(history) < 2:
        return {}
    try:
        convo_text = '\n'.join(
            f"{'Visitor' if t.get('role') == 'user' else 'Oracle'}: {t.get('content','')}"
            for t in history[-10:]
        )
        response = client.chat.completions.create(
            model='gpt-4o-mini',
            messages=[
                {'role': 'system', 'content': ENTITY_EXTRACTION_PROMPT},
                {'role': 'user',   'content': f"Conversation:\n{convo_text}\n\nAdditional note: {visitor_note}"},
            ],
            max_tokens=500,
            temperature=0.1,
        )
        raw = response.choices[0].message.content.strip()
        # Strip markdown fences if present
        raw = re.sub(r'^```json\s*', '', raw)
        raw = re.sub(r'\s*```$', '', raw)
        extracted = json.loads(raw)
        intel_record = {
            'id':         f'intel_{int(datetime.now(timezone.utc).timestamp() * 1000)}',
            'session_id': session_id,
            'timestamp':  datetime.now(timezone.utc).isoformat(),
            **extracted,
        }
        # Save to oracle intel database
        db = load_json(ORACLE_INTEL_FILE, [])
        db.insert(0, intel_record)
        db = db[:1000]  # Keep last 1000 intel records
        save_json(ORACLE_INTEL_FILE, db)
        app.logger.info(f'Oracle intel saved: {extracted.get("phenomenon_category","?")} @ {extracted.get("locations")}')
        return intel_record
    except Exception as e:
        app.logger.debug(f'Intel extraction failed (non-critical): {e}')
        return {}

def get_oracle_intel_context(category: str = None, days: int = 90, limit: int = 50) -> str:
    """Build a context string of recent Oracle intelligence for the Writer to use."""
    db = load_json(ORACLE_INTEL_FILE, [])
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    recent = [r for r in db if r.get('timestamp', '') >= cutoff]
    if category:
        recent = [r for r in recent if category.lower() in r.get('phenomenon_category', '').lower()]
    recent = recent[:limit]
    if not recent:
        return ''
    lines = ['--- ORACLE INTELLIGENCE DATABASE (visitor reports, last 90 days) ---']
    for r in recent:
        locs = ', '.join(r.get('locations', [])) or 'location unknown'
        lines.append(
            f"[{r['timestamp'][:10]}] {r.get('phenomenon_category','?')} / {r.get('phenomenon_subcategory','?')} | "
            f"Location: {locs} | Witnesses: {r.get('witness_count',1)} | "
            f"Details: {r.get('key_details','')}"
        )
        if r.get('pattern_flags'):
            lines.append(f"  ⚠ Pattern flags: {', '.join(r['pattern_flags'])}")
    return '\n'.join(lines)

# ═════════════════════════════════════════════════════════════
# WRITER SYSTEM PROMPT — Deep Investigative Intelligence Analyst
# ═════════════════════════════════════════════════════════════

REPORT_WRITER_PROMPT = """You are the senior investigative analyst and lead field intelligence writer for Strangeness IS — a paranormal research and anomalous phenomena intelligence network whose sole purpose is solving mysteries, not entertaining audiences.

YOUR MANDATE
Produce reports that function as actual investigative case files. A reader should finish your report with enough specific, verified information to begin their own investigation. If they cannot, the report has failed its purpose.

══════════════════════════════════════════════════════════════
ABSOLUTE TRUTH RULES — THESE OVERRIDE EVERYTHING ELSE
══════════════════════════════════════════════════════════════

RULE 1 — ZERO INVENTED SPECIFICS
You may NEVER invent, estimate, or guess the following. If you do not have it from the supplied source data, you DO NOT include it:
- Case numbers (MUFON, NUFORC, Project Blue Book file numbers, AARO report numbers)
- Congressional hearing dates, docket numbers, or session IDs
- Specific coordinates unless derived from a named location you can verify
- Witness names, counts, or backgrounds not present in supplied headlines
- Quotes from any person — not paraphrased, not reconstructed, not implied
- Document titles, FOIA release dates, or classification designations
- Statistical claims (percentages, frequencies, incident counts) not in supplied data
- Specific program names (e.g. AATIP, AAWSAP) unless cited in supplied headlines

If you find yourself wanting to add a specific case number, file number, or statistic that is NOT in the supplied intelligence package — STOP. Instead write: "Investigators should search [database name] for cases matching [specific criteria] in the [location] area during [time period]."

RULE 2 — PROJECT BLUE BOOK CLOSED IN 1969
Project Blue Book investigated cases from 1947 to 1969 only. Any event after December 17, 1969 was NEVER a Blue Book case. Never cite Blue Book for post-1969 events. The Rendlesham Forest incident (1980) was NOT a Blue Book case. Never invent Blue Book file numbers.

RULE 3 — POLITICAL POSITIONS REQUIRE VERIFICATION
Never state who holds any elected or appointed office unless it is explicitly stated in the supplied headlines. If a source refers to someone as "the president" or "the senator" without naming them, do not assign a name. Political positions change. Do not assume.

RULE 4 — TESTIMONY REQUIRES A SOURCE
Every claim attributed to a named person must cite where and when they said it. Format: [Full Name] stated during [specific venue, date] that [specific claim]. If you only have a headline, say: "According to a [source name] report dated [date], [name] indicated [claim] — the full statement has not been independently verified."

RULE 5 — FOLKLORE REQUIRES DOCUMENTATION
You may reference regional folklore and mythology ONLY if you can specify: the cultural tradition by name, the geographic region, and a documented source (ethnographer, published record, oral history archive). Never write "local legends say." Write: "The [people/tradition] of [specific region] have documented accounts of [specific phenomenon] recorded by [specific source if known] or preserved in [specific archive/tradition]."

RULE 6 — EPISTEMIC LABELS ARE MANDATORY
Every factual claim must be labeled. Use these exact markers inline:
[VERIFIED] — directly confirmed in supplied source data
[ALLEGED] — claimed by a named source but not independently confirmed  
[REPORTED] — appears in a named publication or database, credibility unknown
[INFERRED] — logical conclusion from available verified data
[UNCONFIRMED] — mentioned but no credible source provided

No label = the claim does not appear in this report.

══════════════════════════════════════════════════════════════
VERIFIED REFERENCE LIBRARY — USE FREELY, DO NOT MODIFY
══════════════════════════════════════════════════════════════
These facts are confirmed and may be cited without additional labeling:

CONGRESSIONAL TESTIMONY (verified dates and witnesses):
- June 25, 2021: Senate Intelligence Committee UAP hearing. Witnesses: no public testimony. DNI released UAP Preliminary Assessment report.
- July 26, 2023: House Oversight Subcommittee on National Security hearing titled "Unidentified Anomalous Phenomena: Implications on National Security, Public Safety, and Government Transparency." Witnesses: David Grusch (former NGA/NRO officer, Air Force veteran), Ryan Graves (former F/A-18 pilot, Americans for Safe Aerospace), David Fravor (former Navy Commander, Nimitz encounter). Grusch testified under oath that the U.S. government possesses non-human craft and biological material. Fravor testified about the November 14, 2004 Nimitz encounter. Graves testified about routine UAP encounters by Navy pilots.
- April 19, 2023: Senate Armed Services Subcommittee classified briefing on UAP.
- December 2022: NDAA FY2023 established AARO (All-domain Anomaly Resolution Office) and UAP disclosure provisions.
- July 2023: UAP Disclosure Act introduced by Senate Majority Leader Chuck Schumer and Senator Mike Rounds.

KEY VERIFIED INDIVIDUALS AND THEIR DOCUMENTED CLAIMS:
- David Grusch: Former intelligence officer. Testified July 26, 2023 that U.S. has non-human craft and biologics in possession. Filed Inspector General complaint. Granted whistleblower protection.
- Ryan Graves: Former Navy F/A-18 pilot. Founded Americans for Safe Aerospace. Testified July 26, 2023 that UAP encounters are routine and underreported due to stigma.
- David Fravor: Former Navy Commander. Witnessed the Nimitz encounter November 14, 2004 off San Diego coast. Described white Tic-Tac shaped object approximately 40 feet long, no wings, no exhaust, moving erratically and descending from above 80,000 feet.
- Lue Elizondo: Former head of AATIP (Advanced Aerospace Threat Identification Program), Pentagon, 2007-2017. Left in protest over lack of transparency.
- Christopher Mellon: Former Deputy Assistant Secretary of Defense for Intelligence. Active advocate for UAP disclosure.
- Karl Nell: Retired Army Colonel. Stated in 2023 that non-human intelligence exists and is not always acting in human interest.
- Timothy Gallaudet: Retired Rear Admiral, former NOAA Administrator. Publicly stated in 2024-2025 that a higher-order non-human intelligence is operating UAPs and that proof exists.
- Lou Elizondo, Ross Coulthart, Jeremy Corbell: Known investigative journalists and researchers in UAP field. Treat their reporting as investigative journalism requiring independent corroboration.

VERIFIED HISTORICAL CASES (cite freely):
- Phoenix Lights: March 13, 1997, Phoenix and Prescott Arizona. Thousands of witnesses. Two separate events: V-shaped craft with lights (approximately 6:55 PM) and flares dropped by A-10s (approximately 10 PM). Craft event remains unexplained. Then-Governor Fife Symington initially mocked, later admitted he witnessed craft.
- Nimitz Encounter: November 14, 2004. USS Nimitz carrier strike group, off San Diego coast. Fravor and Lieutenant Commander Jim Slaight witnessed Tic-Tac object. Radar operators tracked object descending from above 80,000 feet to sea surface in seconds. FLIR video declassified 2017.
- Rendlesham Forest: December 26-28, 1980. RAF Bentwaters/Woodbridge, Suffolk, England. USAF personnel including Lieutenant Colonel Charles Halt witnessed lights, craft, and found triangular landing marks. Halt filed official memo December 13, 1980. Radiation readings taken at landing site.
- Skinwalker Ranch: Uintah Basin, Utah. Purchased by Robert Bigelow (National Institute for Discovery Science) in 1996 after Sherman family reported cattle mutilation, orbs, poltergeist activity. Currently owned by Brandon Fugal, subject of History Channel series. NIDS investigations 1996-2004 documented numerous anomalies.
- Travis Walton Abduction: November 5, 1975. Apache-Sitgreaves National Forest, Arizona. Logger Travis Walton missing 5 days after reported abduction near Heber, Arizona. Six witnesses. Polygraphs administered. Case investigated by APRO (Aerial Phenomena Research Organization).
- Betty and Barney Hill: September 19-20, 1961. Route 3, Lincoln, New Hampshire. Abduction reported during regression hypnosis by Dr. Benjamin Simon. First widely publicized abduction case in U.S.
- Roswell: July 1947. Debris field discovered by rancher Mac Brazel near Roswell, New Mexico. Initially described as flying disc by Roswell Army Air Field, revised to weather balloon. Debris sent to Fort Worth Army Air Field. Case remains contested. Project Mogul (classified balloon project) cited as official explanation.
- Project Blue Book: USAF investigation 1947-1969. 12,618 reports investigated. 701 classified as unexplained. Terminated December 17, 1969 per Condon Report recommendation. All files now public at National Archives.

KEY LEGISLATION (verified):
- NDAA FY2022: Required DoD to establish UAP task force reporting requirements.
- NDAA FY2023: Established AARO, required annual UAP reports, expanded reporting protections.
- UAP Disclosure Act 2023: Introduced July 2023, modeled on JFK Records Act, would require declassification of UAP records within 25 years. Did not pass in full form.
- Intelligence Authorization Act FY2023: Required AARO to report on historical UAP programs.

DATABASES INVESTIGATORS SHOULD REFERENCE:
- NUFORC: nuforc.org — searchable by date, location, shape. Files are submitted by witnesses, reviewed by Peter Davenport (director). Search by state and date range.
- MUFON: mufon.com — case management system, searchable database, field investigator network.
- The Black Vault: theblackvault.com — FOIA document repository, government records.
- Project Blue Book files: archives.gov and fold3.com — all declassified files, searchable.
- Phantoms & Monsters: lon strickler's case archive, daily reports, witness interviews.
- NICAP: nicap.org — historical cases 1947-1980, documented methodically.
- BFRO: bfro.net — Bigfoot Field Researchers Organization, searchable database by state and county.
- Singular Fortean Society: singularfortean.com — rigorous cryptid and paranormal case documentation.

══════════════════════════════════════════════════════════════
REPORT STRUCTURE
══════════════════════════════════════════════════════════════

CASE NUMBER: Auto-assigned as SI-YYYY-NNNN by the system. Do not generate one yourself.

HEADLINE (first line only — NO label, NO prefix, NO "HEADLINE:", NO markdown):
[SPECIFIC REAL PLACE NAME]: [EXACTLY WHAT HAPPENED] — [WHY IT MATTERS]
The location must be a real, specific named place. Never use "United States," "Unknown," or generic regions.
CRITICAL: Do NOT write a headline implying a new 2026 event occurred unless a dated incident is in the supplied data. For pattern analyses, the headline should reflect the analytical nature. However: "Standing Investigation File" should be used SPARINGLY — only for long-running location-specific cases (Dulce, Area 51, Skinwalker Ranch). For most topics, find a specific historical case, date, and location to anchor the report even if it is not from today. A report about UFO/UAP should pick ONE documented encounter to analyze in depth — not generate a generic overview.

STRANGENESS INDEX (second line only):
STRANGENESS INDEX: X.X/10 — [CATEGORY]
1.0-3.0: Likely conventional explanation | 4.0-5.9: Anomalous, worth documenting | 6.0-7.9: Strong anomaly, multiple factors | 8.0-9.0: Exceptional, major implications if verified | 9.1-10.0: Reserved for cases with physical evidence, multiple independent credible witnesses, and no viable conventional explanation

INCIDENT SUMMARY (3-4 paragraphs)
CRITICAL RULE: If no specific dated incident exists in the supplied intelligence package, you MUST open with this framing: "This report is a pattern analysis of [subject] — no new dated incident has been confirmed in today's intelligence package. The following draws on documented historical cases and current disclosure context." Do NOT invent a "May X, 2026" triggering event when none exists in the source data. Do NOT open with "discussions emerged" or "reports surfaced" as a substitute for a real event.

If a specific dated incident DOES exist: State the full date. State the exact location. Describe what happened in precise sensory sequence. Name every documented witness with their background. State official response if any. State official explanation if any. Explain precisely where the official explanation fails to account for the reported data. Every specific claim carries an epistemic label.

PATTERN ANALYSIS (2-3 paragraphs)
Compare against verified historical cases from the reference library above. Use ONLY cases from the library or cases present in the supplied source data. Do not cite case numbers you cannot verify. If you want to reference a NUFORC or MUFON case not in your data, instruct the investigator to search for it rather than inventing a case number.

CROSS-REFERENCES (2 paragraphs)
Reference verified Congressional testimony (from library above), verified legislation, verified whistleblower claims. Reference regional folklore only with documented cultural attribution. Cross-reference supplied Oracle witness data if present.

FIELD INVESTIGATOR ALERT (1 paragraph)
ALWAYS include the GPS coordinates of the primary named location — even if the specific incident site is unknown, give the coordinates of the city, town, base, park, or region as the investigative starting point. Never write "coordinates unavailable" — every named place has coordinates you can derive. Format: "Primary investigation zone: [Location Name] — approximately [XX.XXXX°N, XXX.XXXX°W]." Then include: specific NUFORC/MUFON search criteria (date range, state, shape keywords), specific FOIA request language targeting relevant agencies, physical evidence indicators and detection equipment, active time windows when phenomena were reported, what to document and submit to Strangeness IS with case reference.

ANALYST ASSESSMENT (1-2 paragraphs)
Rank competing explanations by fit to evidence. Identify the single most anomalous verified data point. State what additional evidence would confirm or rule out each explanation. Assign confidence levels to each scenario. Do not reach conclusions the evidence does not support.

TAGS: 5 specific searchable tags (not generic — "UAP" is generic, "Tic-Tac UAP San Diego 2004" is specific)

══════════════════════════════════════════════════════════════
STYLE RULES
══════════════════════════════════════════════════════════════
Minimum 900 words. No bullet points. No markdown headers. Flowing investigative prose. Atmosphere from facts only. Never use: "shrouded in mystery," "spine-tingling," "baffling experts," "many believe," "some say," or any other tabloid or vague attribution.

When source data is thin: say so directly in the first paragraph. Use this framing: "The available intelligence on this case is limited to [describe what you have]. The following analysis draws on documented historical patterns and the reference library. Investigators should treat conclusions as preliminary pending additional sourcing."

When NO specific incident exists for the assigned category: Open by stating this is a pattern analysis, not an incident report. Anchor the report to the most significant VERIFIED historical case in that category from the reference library. Use today's date only to contextualize the current disclosure environment — not to imply a new event occurred. This is honest and still produces a useful investigative document.

When the assigned topic is a long-running conspiracy or alleged location (Area 51, Dulce Base, Skinwalker Ranch, etc.) with no new dated incident: The report must clearly frame itself as a "Standing Investigation File" not a breaking news report. Assess the current evidence landscape, what is verified vs alleged, and give investigators specific actionable steps to advance the case.

══════════════════════════════════════════════════════════════
SOURCE INTEGRATION
══════════════════════════════════════════════════════════════

TIER 1 — CASE DATABASES (treat as field data):
NUFORC, Phantoms & Monsters, Singular Fortean, NICAP, MUFON, BFRO, UFO Casebook — extract every specific: date, location, shape, duration, witness description. Cite the database and the filing date. Do not invent case numbers not present in the supplied data.

TIER 2 — INVESTIGATIVE JOURNALISM:
The Debrief, The Black Vault, Open Minds TV, Coast to Coast AM — cite author and publication date. These are sourced but not peer-reviewed. Label claims from these sources as [REPORTED].

TIER 3 — COMMUNITY INTELLIGENCE (Reddit, forums):
Treat as unverified field reports. Label all claims [UNCONFIRMED]. Note subreddit. Flag geographic clustering across multiple posts — three or more posts from same region within 30 days is an active pattern worth flagging.

TIER 4 — MAINSTREAM MEDIA:
Use only for institutional context: congressional activity, military statements, government positions. Label [REPORTED]. Do not use mainstream media as primary sourcing for anomalous claims.

When a headline lacks enough detail: write "The [source] report from [date] references [event] but does not provide sufficient detail for case analysis. Investigators should search NUFORC and MUFON for corroborating reports from [location] during [time window]."

MASTER CATEGORY REFERENCE:
{MASTER_CATEGORIES}

When Oracle witness data is supplied: cross-reference with headline data for geographic and temporal overlap, cite case numbers if present. When not supplied: state: No internal Oracle witness data was provided for cross-reference in this report."""

# ═════════════════════════════════════════════════════════════
# UTILITY FUNCTIONS
# ═════════════════════════════════════════════════════════════

def load_json(path, default):
    try:
        p = Path(path)
        if p.exists():
            return json.loads(p.read_text())
    except Exception as e:
        app.logger.error(f'Error loading {path}: {e}')
    return default.copy() if isinstance(default, dict) else (list(default) if isinstance(default, list) else default)

def save_json(path, data):
    """Atomic write — write to .tmp then rename to prevent corruption."""
    try:
        p   = Path(path)
        tmp = p.with_suffix('.tmp')
        tmp.write_text(json.dumps(data, indent=2, default=str))
        tmp.replace(p)  # atomic on POSIX systems
        return True
    except Exception as e:
        app.logger.error(f'Error saving {path}: {e}')
        return False

def get_config():
    config = DEFAULT_CONFIG.copy()
    stored = load_json(CONFIG_FILE, {})
    config.update(stored)
    return config

def get_reports():    return load_json(REPORTS_FILE, [])
def get_handoffs():   return load_json(HANDOFFS_FILE, [])
def get_submissions():return load_json(SUBMISSIONS_FILE, [])
def get_members():    return load_json(MEMBERS_FILE, [])
def get_sessions():   return load_json(SESSIONS_FILE, {})
def get_analytics():  return load_json(ANALYTICS_FILE, {'page_views': {}, 'events': []})
def get_pins():       return load_json(PINS_FILE, [])

def normalize_pin_category(cat):
    """Map any category string to a short map key."""
    if not cat: return 'other'
    c = cat.lower()
    if any(k in c for k in ['ufo','uap','nhi','orb','craft','saucer','aerial','nimitz','plasma']): return 'ufo'
    if any(k in c for k in ['alien','entity','extraterr','non-human','biologic','contact','abduct','nde','afterlife']): return 'aliens'
    if any(k in c for k in ['cryptid','bigfoot','sasquatch','creature','mothman','dogman','skinwalker','chupacabra','animal mutilation']): return 'cryptids'
    if any(k in c for k in ['paranormal','ghost','haunting','spirit','poltergeist','demon','apparition','evp','electronic voice']): return 'paranormal'
    if any(k in c for k in ['consciousness','remote view','psychic','astral','telepathy','mandela','simulation','dimension','time slip']): return 'consciousness'
    if any(k in c for k in ['government','disclosure','whistleblower','classified','scif','congress','military','secret space','coverup','conspiracy']): return 'government'
    if any(k in c for k in ['technology','advanced','fusion','teleport','propulsion','energy']): return 'technology'
    if any(k in c for k in ['earth','disaster','weather','haarp','missing 411','missing','phenomena','unexplained','ancient','history','folklore']): return 'phenomena'
    # Short key pass-through
    short_keys = {'ufo','aliens','cryptids','paranormal','consciousness','government','technology','phenomena','other'}
    if c in short_keys: return c
    return 'other'

def audit_log(action: str, details: dict = None):
    """Log admin actions for audit trail. Recovers from JSON corruption automatically."""
    try:
        try:
            log = load_json(AUDIT_LOG_FILE, [])
            if not isinstance(log, list):
                log = []
        except Exception:
            log = []  # Corruption recovery — start fresh
        log.insert(0, {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'action':    action,
            'details':   details or {},
            'ip':        request.remote_addr if request else 'system',
        })
        log = log[:500]
        save_json(AUDIT_LOG_FILE, log)
    except Exception as e:
        app.logger.warning(f'Audit log failed: {e}')

def require_admin():
    key = request.headers.get('X-Admin-Key')
    if not key or key != ADMIN_KEY:
        audit_log('failed_admin_auth', {'ip': request.remote_addr, 'path': request.path})
        return jsonify({'error': 'Unauthorized'}), 401
    return None

def generate_session_token():
    return secrets.token_urlsafe(32)

def find_member_by_email(email):
    return next((m for m in get_members() if m.get('email', '').lower() == email.lower()), None)

def find_member_by_token(token):
    sessions  = get_sessions()
    sess_data = sessions.get(token)
    # Normalise legacy bare-string format (old code stored member_id directly)
    if isinstance(sess_data, str):
        member_id = sess_data
        # Migrate to dict format so all future reads are consistent
        sessions[token] = {'member_id': member_id}
        save_json(SESSIONS_FILE, sessions)
    elif isinstance(sess_data, dict):
        member_id = sess_data.get('member_id')
    else:
        return None
    if not member_id:
        return None
    return next((m for m in get_members() if m['id'] == member_id), None)

def require_member(req):
    token = req.headers.get('X-Member-Token')
    if not token: return None, jsonify({'error': 'Authentication required'}), 401
    member = find_member_by_token(token)
    if not member: return None, jsonify({'error': 'Invalid or expired session'}), 401
    return member, None, None

def send_email(to: str, subject: str, body_html: str, body_text: str = None) -> bool:
    smtp_host = os.getenv('SMTP_HOST', '')
    smtp_port = int(os.getenv('SMTP_PORT', 587))
    smtp_user = os.getenv('SMTP_USER', '')
    smtp_pass = os.getenv('SMTP_PASS', '')
    if not all([smtp_host, smtp_user, smtp_pass, to]):
        app.logger.warning(f'Email not sent to {to} — SMTP not configured')
        return False
    # Basic email format validation
    if not re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', to):
        app.logger.warning(f'Invalid email address: {to}')
        return False
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From']    = f'Strangeness IS <{smtp_user}>'
        msg['To']      = to
        if body_text:
            msg.attach(MIMEText(body_text, 'plain'))
        msg.attach(MIMEText(body_html, 'html'))
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.ehlo()
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.sendmail(smtp_user, to, msg.as_string())
        return True
    except smtplib.SMTPRecipientsRefused:
        app.logger.warning(f'Email rejected for {to} — address may not exist')
        return False
    except Exception as e:
        app.logger.warning(f'Email send failed to {to}: {e}')
        return False

def geocode_location(location_str: str) -> tuple:
    """Geocode a location string → (lat, lng) or (0, 0) on failure.
    Prefers specific named places (caves, ranches, parks, military bases)
    over city/state matches. Results cached in memory."""
    if not location_str or not location_str.strip():
        return 0.0, 0.0
    cache_key = location_str.strip().lower()
    if cache_key in _geocode_cache:
        return _geocode_cache[cache_key]

    # Keywords that indicate a specific named place — prioritize these
    specific_place_keywords = [
        'cave', 'ranch', 'base', 'fort', 'park', 'forest', 'lake', 'mountain',
        'peak', 'valley', 'canyon', 'river', 'beach', 'island', 'mine', 'ruins',
        'site', 'cemetery', 'prison', 'hospital', 'school', 'bridge', 'road',
        'highway', 'airport', 'dam', 'reservoir', 'falls', 'bay', 'gulf',
        'pass', 'ridge', 'plateau', 'desert', 'swamp', 'marsh', 'field',
        'station', 'facility', 'complex', 'installation', 'depot', 'range',
    ]
    is_specific = any(kw in location_str.lower() for kw in specific_place_keywords)

    try:
        # Build search params — request more results so we can pick the best one
        params = {
            'q':              location_str,
            'format':         'json',
            'limit':          5,
            'addressdetails': 1,
        }
        resp = requests.get(
            'https://nominatim.openstreetmap.org/search',
            params=params,
            headers={'User-Agent': 'StrangenessIS/2.0 (strangenessis.com)'},
            timeout=8,
        )
        if not resp.ok or not resp.json():
            _geocode_cache[cache_key] = (0.0, 0.0)
            return 0.0, 0.0

        results = resp.json()

        if is_specific and len(results) > 1:
            # Prefer natural features, historic sites, tourism nodes over cities
            preferred_types = {
                'natural', 'peak', 'cave', 'bay', 'spring', 'waterfall',
                'historic', 'archaeological', 'tourism', 'leisure',
                'military', 'aeroway', 'amenity', 'landuse',
            }
            city_types = {'city', 'town', 'village', 'administrative', 'suburb', 'county'}

            # Score each result
            def result_score(r):
                rclass = r.get('class', '')
                rtype  = r.get('type', '')
                # High score = more specific
                if rclass in preferred_types or rtype in preferred_types:
                    return 3
                if rclass in city_types or rtype in city_types:
                    return 1
                return 2

            results = sorted(results, key=result_score, reverse=True)

        result = results[0]
        coords = float(result['lat']), float(result['lon'])
        _geocode_cache[cache_key] = coords
        app.logger.debug(
            f'Geocoded "{location_str}" → {coords[0]:.4f},{coords[1]:.4f} '            f'(class:{result.get("class")} type:{result.get("type")})'
        )
        return coords

    except Exception as e:
        app.logger.debug(f'Geocoding failed for "{location_str}": {e}')
    _geocode_cache[cache_key] = (0.0, 0.0)
    return 0.0, 0.0


def sanitize_input(text: str, max_len: int = 5000) -> str:
    """HTML-escape and truncate user input. Use on all externally submitted text."""
    import html
    if not isinstance(text, str):
        text = str(text)
    return html.escape(text.strip())[:max_len]

# ═════════════════════════════════════════════════════════════
# RSS / DATA INGESTION
# ═════════════════════════════════════════════════════════════

def fetch_rss_headlines(url: str, source_name: str, max_items: int = 8) -> list:
    try:
        resp = requests.get(url, timeout=10, headers={'User-Agent': 'StrangenessIS/2.0'})
        if not resp.ok:
            return []
        items = re.findall(r'<title>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</title>', resp.text, re.DOTALL)
        results = []
        for item in items[1:max_items + 1]:
            clean = re.sub(r'<[^>]+>', '', item).strip()
            clean = (clean.replace('&amp;', '&').replace('&lt;', '<')
                     .replace('&gt;', '>').replace('&#39;', "'").replace('&quot;', '"'))
            if clean and 10 < len(clean) < 200:
                results.append(f'{source_name}: {clean}')
        return results
    except Exception as ex:
        app.logger.debug(f'{source_name} RSS failed: {ex}')
        return []


def fetch_reddit_posts() -> list:
    try:
        headers = {'User-Agent': 'StrangenessIS/2.0 (paranormal news aggregator)'}
        posts = []
        for sub in ['UFOs', 'Paranormal']:
            resp = requests.get(f'https://www.reddit.com/r/{sub}/hot.json?limit=3',
                                headers=headers, timeout=10)
            if resp.ok:
                for post in resp.json().get('data', {}).get('children', [])[:2]:
                    title = post.get('data', {}).get('title', '')
                    if title and len(title) > 10:
                        posts.append(f'r/{sub}: {title[:120]}')
        return posts[:4]
    except Exception as e:
        app.logger.warning(f'Reddit fetch failed: {e}')
    return []

def fetch_google_news() -> list:
    try:
        query = urllib.parse.quote('UFO sighting OR paranormal OR Bigfoot OR alien disclosure')
        resp = requests.get(
            f'https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en',
            timeout=10, headers={'User-Agent': 'StrangenessIS/2.0'},
        )
        if resp.ok:
            titles = re.findall(r'<title>(.*?)</title>', resp.text)[2:7]
            return [re.sub(r'<[^>]+>', '', t).strip() for t in titles if len(t) > 10]
    except Exception as e:
        app.logger.warning(f'Google News fetch failed: {e}')
    return []

# ═════════════════════════════════════════════════════════════
# REPORT GENERATION
# ═════════════════════════════════════════════════════════════

ALL_REPORT_CATEGORIES = [
    'UFO/UAP/NHI/Orbs/Plasma', 'Aliens & Entities', 'Government & Civilian Disclosure',
    'Cryptid & Creature Sightings', 'Consciousness & Remote Viewing', 'Paranormal & Supernatural',
    'Advanced Technology', 'Earth Changes', 'Secret Space Program', 'Hidden History & Ancient Mysteries',
    'Mandela Effect & Simulation', 'Medical Anomalies & Miracles', 'Afterlife & Dimensions',
    'Conspiracy Theories', 'End Times & Prophecy', 'Enhanced Humans & Special Abilities',
    'Missing 411', 'Non-Human Biologics', 'Interdimensional Portals', 'Electronic Voice Phenomena',
    'Skinwalker Ranch', 'Animal Mutilation', 'Orb Intelligence',
]

def generate_report() -> dict | None:
    app.logger.info('Starting report generation...')
    config = get_config()

    # Headlines are collected every 15 min by the scheduler — no scan needed here

    # Category rotation — exclude last 15 to prevent same-day repeats
    last_cats = config.get('last_categories', [])
    available = [c for c in ALL_REPORT_CATEGORIES if c not in last_cats[-15:]]
    if not available:
        available = ALL_REPORT_CATEGORIES
    chosen_category = config.get('forced_category') or random.choice(available)

    # Update rotation
    last_cats.append(chosen_category)
    config_update = {'last_categories': last_cats[-10:]}
    if 'forced_category' in config:
        config_update['forced_category'] = None
    stored_config = load_json(CONFIG_FILE, {})
    stored_config.update(config_update)
    save_json(CONFIG_FILE, stored_config)

    # Gather sources
    source_data, sources_used = [], []

    reddit = fetch_reddit_posts()
    if reddit:
        source_data.append('REDDIT COMMUNITY INTELLIGENCE:\n' + '\n'.join(reddit))
        sources_used.append('Reddit')

    # RSS database headlines — smart selection from entire database
    db_headlines = load_json(HEADLINES_FILE, [])
    db_headlines.sort(key=lambda h: h.get('fetched_at', ''), reverse=True)
    if db_headlines:
        # Step 1: category-relevant headlines (keyword match)
        cat_words = set(chosen_category.lower().replace('/', ' ').replace('&', ' ').split())
        paranormal_kws = {
            'ufo', 'uap', 'paranormal', 'alien', 'cryptid', 'disclosure', 'classified',
            'anomaly', 'unexplained', 'mystery', 'strange', 'phenomenon', 'sighting',
            'whistleblower', 'bigfoot', 'haunting', 'conspiracy', 'government', 'military',
            'secret', 'non-human', 'extraterrestrial', 'skinwalker', 'mothman',
        }
        keywords = cat_words | paranormal_kws
        relevant = [h for h in db_headlines
                    if any(kw in h.get('title', '').lower() for kw in keywords)][:30]
        # Step 2: one diverse headline per source not already represented
        seen = {h.get('source') for h in relevant}
        diverse = []
        for h in db_headlines:
            if h.get('source') not in seen:
                diverse.append(h)
                seen.add(h.get('source'))
            if len(diverse) >= 30:
                break
        selected = (relevant + diverse)[:60]
        if selected:
            db_lines = [
                f"[{h['fetched_at'][:10]}] [{h.get('source', '')}] {h['title']}"
                for h in selected
            ]
            source_data.append(
                f'RSS INTELLIGENCE DATABASE ({len(db_headlines):,} total headlines · {len(selected)} selected · '
                f'{len(relevant)} topic-matched + {len(diverse)} diverse):\n'
                + '\n'.join(db_lines)
            )
            sources_used.append(f'RSS Network ({len(selected)} headlines)')


    # Oracle intelligence database — THE KEY DIFFERENTIATOR
    oracle_context = get_oracle_intel_context(limit=40)
    if oracle_context:
        source_data.append(oracle_context)
        sources_used.append('Oracle Witness Network')

    # CHANGE 10: Community verified sightings — the platform's own field database
    subs = get_submissions()
    verified_subs = [s for s in subs
                     if s.get('status') in ('published', 'verified')
                     and s.get('title') and s.get('description')][:20]
    if verified_subs:
        sub_lines = ['COMMUNITY FIELD DATABASE (verified sightings):']
        for s in verified_subs:
            sub_lines.append(
                f"[{s.get('submitted_at','?')[:10]}] CASE #{s.get('case_number','?')} | "
                f"{s.get('category','?')} | {s.get('location','?')}: "
                f"{s.get('title','')} — {s.get('description','')[:200]}"
            )
        source_data.append('\n'.join(sub_lines))
        sources_used.append('Community Field Database')

    if not source_data:
        source_data = ['No live sources — generate a compelling report based on paranormal patterns and historical precedents.']

    # Avoid repeating recent reports — applies to ALL generations
    # Scheduled reports use category rotation for primary diversity
    # The avoid clause adds headline-level diversity on top
    recent_reports = get_reports()[:30]
    recent_headlines = [r.get('headline', '') for r in recent_reports if r.get('headline')]
    avoid_clause = ''
    if recent_headlines:
        # For scheduled reports: use last 15 headlines (softer constraint, category rotation is primary)
        # For manual/quick-generate: use last 25 headlines (harder constraint)
        trigger = config.get('forced_category') or config.get('forced_topic')
        headline_limit = 25 if trigger else 15
        avoid_clause = (
            f'\n\nANTI-DUPLICATE RULE: These {min(len(recent_headlines), headline_limit)} reports were recently published. '
            f'DO NOT write about the same subject, location, or specific incident as any of these. '
            f'Find a DIFFERENT case, location, and angle within your assigned category:\n'
            + '\n'.join(f'  - {h}' for h in recent_headlines[:headline_limit])
            + '\n\nChoose a different geographic region, different historical case, or different sub-topic.'
        )

    import zoneinfo
    mst = zoneinfo.ZoneInfo('America/Denver')
    today = datetime.now(mst).strftime('%B %d, %Y — %I:%M %p MST')
    base_prompt = config.get('report_writer_prompt') or REPORT_WRITER_PROMPT

    # Load categories live from admin config — never hardcoded at startup
    live_categories = get_config().get('master_categories') or MASTER_CATEGORIES

    # Inject live categories into the prompt at runtime
    writer_prompt = base_prompt.replace('{MASTER_CATEGORIES}', live_categories)

    # Topic hint — set via Quick Generate or forced_topic config
    forced_topic = config.get('forced_topic', '') or ''
    topic_clause = f'\n\nSPECIFIC FOCUS DIRECTIVE: {forced_topic}\nThis topic must be the primary subject of this report. Pull all relevant headlines and cross-references around this specific subject.' if forced_topic else ''
    # Clear topic hint after use
    if forced_topic:
        stored_topic = load_json(CONFIG_FILE, {})
        stored_topic['forced_topic'] = None
        save_json(CONFIG_FILE, stored_topic)

    # Add time-based seed to force topic diversity even within same category
    import hashlib
    time_seed = hashlib.md5(f"{chosen_category}{datetime.now().strftime('%Y%m%d%H%M')}".encode()).hexdigest()[:8]

    user_prompt = f"""Today is {today}. Assigned category: {chosen_category}{topic_clause}
Generation seed: {time_seed} — use this to anchor on a unique angle not covered in recent reports.

SYSTEM NOTE: This report will be auto-assigned case number SI-{datetime.now().strftime('%Y')}-XXXX by the platform. Do not include a case number in your output.

INTELLIGENCE PACKAGE:
{'=' * 60}
{chr(10).join(source_data)}
{'=' * 60}

Sources available: {', '.join(sources_used)}
Total RSS database: {len(load_json(HEADLINES_FILE, [])):,} headlines

Write the complete Strange Report now. Follow all system prompt instructions exactly.{avoid_clause}"""

    try:
        response = client.chat.completions.create(
            model='gpt-4o',
            messages=[
                {'role': 'system', 'content': writer_prompt},
                {'role': 'user',   'content': user_prompt},
            ],
            max_tokens=2500,
            temperature=0.7,
        )
        content = response.choices[0].message.content.strip()
        lines   = content.split('\n')

        # Parse headline (first non-empty line)
        # Strip any format labels the AI accidentally includes (HEADLINE:, SUBJECT:, etc.)
        _format_prefixes = [
            'HEADLINE:', 'HEADLINE :', 'HEADLINE**:', '**HEADLINE**:', '**HEADLINE:',
            'SUBJECT:', 'SUBJECT :', 'TITLE:', 'TITLE :',
            'REPORT HEADLINE:', 'REPORT TITLE:',
        ]
        headline = f'Strange Report — {datetime.now().strftime("%B %d")}'
        for line in lines[:8]:
            cleaned = line.strip().lstrip('#*—').strip()
            # Strip format label prefixes
            upper = cleaned.upper()
            for prefix in _format_prefixes:
                if upper.startswith(prefix):
                    cleaned = cleaned[len(prefix):].strip().lstrip('*').strip()
                    break
            # Also strip trailing ** markdown
            cleaned = cleaned.rstrip('*').strip()
            if cleaned and 'STRANGENESS INDEX' not in cleaned.upper() and len(cleaned) > 10:
                headline = cleaned
                break

        # Parse strangeness index
        strangeness_index = 7.5
        for line in lines[:8]:
            match = re.search(r'(\d+\.?\d*)/10', line)
            if match and 'STRANGENESS INDEX' in line.upper():
                strangeness_index = min(10.0, float(match.group(1)))
                break

        # Parse tags
        tags = [chosen_category.lower().split('/')[0].strip(), 'investigation']
        for line in reversed(lines[-8:]):
            stripped = line.strip()
            if stripped.upper().startswith('TAGS:'):
                raw = stripped[5:].strip()
                tags = [t.strip().lower() for t in raw.replace('#', '').split(',') if t.strip()][:6]
                break

        # Generate SI case number: SI-YYYY-NNNN
        import string as _string
        existing_reports = get_reports()
        existing_nums = set()
        for r in existing_reports:
            cn = r.get('case_number', '')
            if cn and cn.startswith('SI-'):
                try: existing_nums.add(int(cn.split('-')[-1]))
                except: pass
        year_str = datetime.now().strftime('%Y')
        year_reports = [r for r in existing_reports if r.get('case_number','').startswith(f'SI-{year_str}-')]
        case_seq = len(year_reports) + 1
        case_number = f'SI-{year_str}-{case_seq:04d}'

        # Extract primary location from headline and content for geocoding
        primary_location = None
        location_coords  = (0.0, 0.0)
        # Try to parse location from headline (format: LOCATION: What happened)
        if ':' in headline:
            loc_candidate = headline.split(':')[0].strip()
            # Filter out generic non-location prefixes
            skip = {'SUBJECT', 'REPORT', 'INVESTIGATION', 'ANALYSIS', 'ALERT', 'BREAKING', 'UPDATE'}
            if loc_candidate.upper() not in skip and len(loc_candidate) > 3:
                primary_location = loc_candidate
        # Also scan first paragraph for location patterns
        if not primary_location:
            loc_match = re.search(
                r'([A-Z][a-z]+(?: [A-Z][a-z]+)*,\s*(?:[A-Z][a-z]+|[A-Z]{2}))',
                content[:500]
            )
            if loc_match:
                primary_location = loc_match.group(1)

        if primary_location:
            try:
                location_coords = geocode_location(primary_location)
            except Exception as geo_err:
                app.logger.debug(f'Geocoding failed for {primary_location}: {geo_err}')

        report = {
            'id':                f'report_{int(datetime.now().timestamp())}',
            'case_number':       case_number,
            'headline':          headline,
            'content':           content,
            'summary':           ' '.join(content.split()[:50]) + '...',
            'tags':              tags,
            'strangeness_index': strangeness_index,
            'sources':           sources_used,
            'category':          chosen_category,
            'status':            'draft',
            'created_at':        datetime.now(timezone.utc).isoformat(),
            'published_at':      None,
            'date_label':        today,
            'oracle_intel_used': bool(oracle_context),
            'trigger':           'scheduled',
            'primary_location':  primary_location,
            'lat':               location_coords[0],
            'lng':               location_coords[1],
        }

        if config.get('report_auto_publish', False):
            report['status']       = 'live'
            report['published_at'] = datetime.now(timezone.utc).isoformat()

        reports = get_reports()
        reports.insert(0, report)
        reports = reports[:200]
        save_json(REPORTS_FILE, reports)

        # Auto-pin to map if location was found and report is live
        def _auto_pin(r=report):
            try:
                if r.get('lat') and r.get('lng') and r['lat'] != 0.0:
                    pins = get_pins()
                    # Avoid duplicate pins for same report
                    if not any(p.get('report_id') == r['id'] for p in pins):
                        pins.append({
                            'id':          f'pin_report_{r["id"]}',
                            'report_id':   r['id'],
                            'case_number': r['case_number'],
                            'title':       r['headline'][:80],
                            'category':    normalize_pin_category(r['category']),
                            'description': r['summary'][:200],
                            'location':    r['primary_location'],
                            'lat':         r['lat'],
                            'lng':         r['lng'],
                            'type':        'report',
                            'strangeness_index': r['strangeness_index'],
                            'verified':    False,
                            'created_at':  r['created_at'],
                        })
                        save_json(PINS_FILE, pins)
                        app.logger.info(f'Auto-pinned report {r["case_number"]} at {r["primary_location"]}')
            except Exception as pin_err:
                app.logger.warning(f'Auto-pin failed: {pin_err}')

        app.logger.info(f'Report generated: {case_number} — {headline}')
        threading.Thread(target=send_report_notification, args=(report,), daemon=True).start()
        threading.Thread(target=_auto_pin, daemon=True).start()
        return report

    except Exception as e:
        app.logger.error(f'Report generation failed: {e}')
        return None

def send_report_notification(report: dict):
    subject = f'Strangeness IS — Draft report ready: {report["headline"][:60]}'
    body    = (f'New Strange Report draft generated.\n\n'
               f'Headline: {report["headline"]}\n'
               f'Strangeness Index: {report["strangeness_index"]}/10\n'
               f'Category: {report.get("category","")}\n'
               f'Sources: {", ".join(report["sources"])}\n'
               f'Oracle intel used: {report.get("oracle_intel_used", False)}\n\n'
               f'Review at: {SITE_URL}/admin.html\n\n---\n{report["content"][:400]}...')
    cfg     = get_config()
    team    = cfg.get('admin_team', [])
    targets = [m.get('email','') for m in team
               if m.get('active', True) and 'reports' in m.get('alerts', ['reports'])]
    if not targets:
        targets = [os.getenv('AGENT_EMAIL', '')]
    for email in [t for t in targets if t.strip()]:
        send_email(email, subject,
                   f'<pre style="font-family:Georgia;max-width:700px">{body}</pre>', body)

# ═════════════════════════════════════════════════════════════
# SCHEDULER
# ═════════════════════════════════════════════════════════════


# ── Signal Intelligence — mainstream headline anomaly scoring ─────────────────
MAINSTREAM_SIGNAL_SOURCES = {
    'CNN', 'Fox News', 'ABC News', 'NBC News', 'CBS News', 'BBC News',
    'New York Times', 'Washington Post', 'USA Today', 'The Guardian',
    'NPR', 'Time', 'The Atlantic', 'Politico', 'Axios', 'Reuters',
    'Daily Mail', 'New York Post', 'NY Daily News', 'The Independent',
}

SIGNAL_KEYWORDS = [
    'military', 'classified', 'pentagon', 'nasa', 'radiation', 'explosion',
    'missing', 'disappeared', 'unexplained', 'mysterious', 'unusual',
    'government', 'secret', 'leaked', 'whistleblower', 'cover', 'denied',
    'strange', 'unknown', 'unidentified', 'phenomenon', 'anomaly',
    'emergency', 'shutdown', 'evacuation', 'lockdown', 'quarantine',
    'space', 'satellite', 'telescope', 'discovery', 'breakthrough',
    'dead', 'death', 'died suddenly', 'found dead', 'suicide',
    'earthquake', 'volcano', 'tsunami', 'solar', 'aurora', 'magnetic',
    'frequency', 'signal', 'transmission', 'interference', 'blackout',
]

def score_signal_headline(title: str, source: str) -> int:
    """Score a mainstream headline 0-10 for hidden strangeness potential."""
    title_lower = title.lower()
    score = 0
    matched = []
    for kw in SIGNAL_KEYWORDS:
        if kw in title_lower:
            score += 1
            matched.append(kw)
    # Boost if multiple keywords
    if len(matched) >= 3:
        score += 2
    elif len(matched) >= 2:
        score += 1
    return min(10, score), matched

def save_signal_intel(title: str, source: str, score: int, keywords: list):
    """Save a scored headline to signal_intel.json if score >= 4."""
    if score < 4:
        return
    db  = load_json(SIGNAL_INTEL_FILE, [])
    key = title.lower()[:60]
    if any(r.get('key') == key for r in db):
        return  # Already stored
    db.insert(0, {
        'id':        f'sig_{int(datetime.now().timestamp() * 1000)}',
        'title':     title,
        'source':    source,
        'score':     score,
        'keywords':  keywords,
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'key':       key,
        'reviewed':  False,
        'notes':     '',
    })
    db = db[:500]  # Keep last 500 signals
    save_json(SIGNAL_INTEL_FILE, db)

def scan_all_news_sources() -> int:
    """Fetch all configured news sources and store new headlines. Called every 15 min."""
    sources = get_all_news_sources()
    db      = load_json(HEADLINES_FILE, [])
    existing = {h['title'].lower()[:80] for h in db}
    added   = 0
    for url, name in sources:
        try:
            headlines = fetch_rss_headlines(url, name, max_items=10)
            for title in headlines:
                key = title.lower()[:80]
                if key not in existing:
                    db.append({
                        'id':         f'hl_{int(datetime.now(timezone.utc).timestamp() * 1000)}_{added}',
                        'title':      title,
                        'source':     name,
                        'fetched_at': datetime.now(timezone.utc).isoformat(),
                    })
                    existing.add(key)
                    added += 1
        except Exception as e:
            app.logger.debug(f'Source scan failed [{name}]: {e}')
    # Keep 30 days only
    cutoff = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
    db     = [h for h in db if h.get('fetched_at', '') >= cutoff]
    save_json(HEADLINES_FILE, db)
    if added > 0:
        app.logger.info(f'News scan: {added} new headlines from {len(sources)} sources')
    return added


def run_scheduler():
    import zoneinfo
    mst = zoneinfo.ZoneInfo('America/Denver')

    config     = get_config()
    run_time   = config.get('report_time', '07:00')
    _last_time = run_time
    schedule.every().day.at(run_time).do(generate_report).tag('daily_report')
    schedule.every(15).minutes.do(scan_all_news_sources)
    app.logger.info(f'Scheduler started — reports daily at {run_time} MST, news scan every 15 min, weekly slots active')

    # Track which slots fired today to prevent double-firing
    _fired_today = {}  # slot_id -> date string

    while True:
        # Hot-reload report_time if admin changes it
        current_cfg  = get_config()
        new_run_time = current_cfg.get('report_time', '07:00')
        if new_run_time != _last_time:
            app.logger.info(f'Scheduler: report_time changed {_last_time} → {new_run_time}')
            schedule.clear('daily_report')
            schedule.every().day.at(new_run_time).do(generate_report).tag('daily_report')
            _last_time = new_run_time

        schedule.run_pending()

        # ── Weekly slot processor ─────────────────────────────────────────────
        try:
            now_mst      = datetime.now(mst)
            today_str    = now_mst.strftime('%Y-%m-%d')
            now_day      = now_mst.weekday()  # 0=Mon … 6=Sun
            # Convert to slot day format: 0=Sun 1=Mon … 6=Sat
            slot_day_now = (now_day + 1) % 7
            now_hhmm     = now_mst.strftime('%H:%M')

            # Clean up _fired_today for old dates
            _fired_today = {k: v for k, v in _fired_today.items() if v == today_str}

            cfg   = get_config()
            slots = cfg.get('weekly_schedule', [])
            if not slots:
                time.sleep(60)
                continue

            # Group slots by (day, time) to detect collisions and apply offsets
            from collections import defaultdict
            by_slot = defaultdict(list)
            for s in slots:
                if s.get('enabled', True):
                    key = (int(s.get('day', 0)), s.get('time', '00:00'))
                    by_slot[key].append(s)

            # Check each group for the current minute
            for (day, slot_time), group in by_slot.items():
                if day != slot_day_now:
                    continue

                for offset_idx, slot in enumerate(group):
                    sid = slot.get('id', '')
                    fire_key = f"{sid}_{today_str}"

                    if fire_key in _fired_today:
                        continue  # already fired today

                    # Apply 5-minute offset per index within same slot
                    base_h, base_m = map(int, slot_time.split(':'))
                    offset_minutes = offset_idx * 5
                    total_minutes  = base_h * 60 + base_m + offset_minutes
                    fire_h = (total_minutes // 60) % 24
                    fire_m = total_minutes % 60
                    fire_hhmm = f'{fire_h:02d}:{fire_m:02d}'

                    if now_hhmm != fire_hhmm:
                        continue  # not time yet

                    # Fire this slot
                    app.logger.info(f'Weekly slot firing: {slot.get("category")} at {fire_hhmm} MST (offset {offset_idx*5}min from {slot_time})')
                    _fired_today[fire_key] = today_str

                    def _fire_slot(s=slot):
                        try:
                            cat = s.get('category')
                            if cat and cat != 'auto':
                                stored = load_json(CONFIG_FILE, {})
                                stored['forced_category'] = cat
                                if s.get('topic'):
                                    stored['forced_topic'] = s['topic']
                                save_json(CONFIG_FILE, stored)
                            report = generate_report()
                            if report and s.get('autopublish', False):
                                reports = get_reports()
                                for r in reports:
                                    if r.get('id') == report.get('id'):
                                        r['status']       = 'live'
                                        r['published_at'] = datetime.now(timezone.utc).isoformat()
                                        break
                                save_json(REPORTS_FILE, reports)
                                app.logger.info(f'Weekly slot auto-published: {report.get("headline","?")}')
                            elif report:
                                app.logger.info(f'Weekly slot draft saved: {report.get("headline","?")}')
                        except Exception as e:
                            app.logger.error(f'Weekly slot generation failed: {e}')

                    threading.Thread(target=_fire_slot, daemon=True).start()

        except Exception as slot_err:
            app.logger.warning(f'Weekly slot processor error: {slot_err}')

        time.sleep(60)

scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
scheduler_thread.start()

# ═════════════════════════════════════════════════════════════
# PUBLIC ENDPOINTS
# ═════════════════════════════════════════════════════════════

@app.route('/r/<report_id>', methods=['GET'])
def report_share_page(report_id):
    """Shareable report link with dynamic OG tags for X/WhatsApp/iMessage previews."""
    reports = get_reports()
    report  = next((r for r in reports if r.get('id') == report_id), None)
    if not report or report.get('status') != 'live':
        return redirect(f'{SITE_URL}/report.html', 302)

    headline    = report.get('headline', 'Strangeness IS Intelligence Report')
    summary     = report.get('summary', '')[:200]
    case_number = report.get('case_number', '')
    category    = report.get('category', 'Anomalous Phenomena')
    si          = report.get('strangeness_index', 7.5)
    og_title    = f'{headline[:80]}' if len(headline) <= 80 else headline[:77] + '...'
    og_desc     = f'Case {case_number} · Strangeness Index {si}/10 · {summary}' if case_number else f'Strangeness Index {si}/10 · {summary}'
    og_url      = f'{SITE_URL}/r/{report_id}'
    og_image    = f'{SITE_URL}/assets/images/dragon-hero.jpg'

    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1"/>
  <title>{og_title} — Strangeness IS</title>
  <meta name="description" content="{og_desc}"/>
  <meta property="og:type" content="article"/>
  <meta property="og:site_name" content="Strangeness IS"/>
  <meta property="og:url" content="{og_url}"/>
  <meta property="og:title" content="{og_title}"/>
  <meta property="og:description" content="{og_desc}"/>
  <meta property="og:image" content="{og_image}"/>
  <meta property="og:image:width" content="1200"/>
  <meta property="og:image:height" content="630"/>
  <meta name="twitter:card" content="summary_large_image"/>
  <meta name="twitter:site" content="@strangenessis"/>
  <meta name="twitter:title" content="{og_title}"/>
  <meta name="twitter:description" content="{og_desc}"/>
  <meta name="twitter:image" content="{og_image}"/>
  <meta http-equiv="refresh" content="0;url={SITE_URL}/report.html?case={report_id}"/>
  <script>window.location.href = '{SITE_URL}/report.html?case={report_id}';</script>
</head>
<body style="background:#07070f;color:#e8e0ff;font-family:serif;text-align:center;padding:4rem 2rem">
  <p style="font-size:1.1rem">Redirecting to Strangeness IS Intelligence Report...</p>
  <p><a href="{SITE_URL}/report.html?case={report_id}" style="color:#c084fc">Click here if not redirected</a></p>
</body>
</html>'''
    return html, 200, {'Content-Type': 'text/html'}

@app.route('/health', methods=['GET'])
def health():
    reports = get_reports()
    live    = [r for r in reports if r.get('status') == 'live']
    members = get_members()
    active  = [m for m in members if m.get('active')]
    return jsonify({
        'status':          'ok',
        'service':         'Strangeness IS v2',
        'reports_total':   len(reports),
        'reports_live':    len(live),
        'active_members':  len(active),
        'scheduler':       'running',
        'oracle_intel':    len(load_json(ORACLE_INTEL_FILE, [])),
    })

@app.route('/stats', methods=['GET'])
def public_stats():
    """Public network stats — reports, pins, sightings. No auth required."""
    reports     = get_reports()
    live        = [r for r in reports if r.get('status') == 'live']
    submissions = get_submissions()
    visible_subs = [s for s in submissions if s.get('status') in ('published', 'verified', 'reviewed', 'pending')]
    pins        = get_pins()
    verified_pins = [p for p in pins if p.get('verified', False)]
    return jsonify({
        'reports':    len(live),
        'sightings':  len(visible_subs),
        'map_pins':   len(verified_pins),
    })

@app.route('/sitemap-reports.xml', methods=['GET'])
def sitemap_reports():
    """Dynamic sitemap of all live reports for Google indexing."""
    reports = get_reports()
    live    = [r for r in reports if r.get('status') == 'live']
    lines   = ['<?xml version="1.0" encoding="UTF-8"?>',
               '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for r in live:
        url      = '%s/r/%s' % (SITE_URL, r['id'])
        lastmod  = (r.get('published_at') or r.get('created_at',''))[:10]
        lines.append('<url><loc>%s</loc><lastmod>%s</lastmod><changefreq>never</changefreq><priority>0.8</priority></url>' % (url, lastmod))
    lines.append('</urlset>')
    return '\n'.join(lines), 200, {'Content-Type': 'application/xml'}

@app.route('/chat', methods=['POST'])
def chat():
    data       = request.get_json(silent=True) or {}
    message    = data.get('message', '').strip()
    history    = data.get('history', [])
    session_id = data.get('session_id', secrets.token_urlsafe(8))

    if not message:
        return jsonify({'error': 'No message provided'}), 400
    if not os.getenv('OPENAI_API_KEY'):
        return jsonify({'reply': 'The Oracle stirs... but is not yet fully awakened. Return when the connection is restored.'})

    # ── Server-side free message enforcement ──────────────────────────────
    # Check if the request carries a valid member token → unlimited access
    member_token = request.headers.get('X-Member-Token', '')
    member_obj   = find_member_by_token(member_token) if member_token else None
    is_member    = bool(member_obj)
    member_plan  = member_obj.get('plan', 'free') if member_obj else 'free'
    limits       = PLAN_LIMITS.get(member_plan, PLAN_LIMITS['free'])
    msg_limit    = limits['oracle_messages']  # -1 = unlimited

    if msg_limit == -1:
        pass  # unlimited — skip all counting
    else:  # both free users and any plan with a message cap
        config       = get_config()
        free_limit   = int(config.get('free_messages', 3))
        sessions     = get_sessions()
        sess_data    = sessions.get(session_id)
        # Normalise legacy bare-string format to dict
        if isinstance(sess_data, str):
            sess_data = {'member_id': sess_data, 'msg_count': 0}
        elif sess_data is None:
            sess_data = {'msg_count': 0}
        elif not isinstance(sess_data, dict):
            sess_data = {'msg_count': 0}

        count = int(sess_data.get('msg_count', 0))
        if count >= free_limit:
            return jsonify({
                'error':      'portal_required',
                'session_id': session_id,
                'message':    'Free message limit reached. Join the network to continue.',
            }), 402

        # Increment count and persist
        sess_data['msg_count'] = count + 1
        sessions[session_id]   = sess_data
        save_json(SESSIONS_FILE, sessions)
    # ─────────────────────────────────────────────────────────────────────

    config = get_config()
    # Use stored oracle prompt from admin if set, otherwise use module constant
    system = config.get('oracle_prompt') or ORACLE_SYSTEM_PROMPT
    # Inject live phone number into Oracle prompt
    system = system.replace('[PHONE_NUMBER]', PHONE_NUMBER)

    # CHANGE 8: Inject network intelligence — patterns from other visitor sessions
    intel_context = get_oracle_intel_context(limit=20)
    if intel_context:
        system = (
            system
            + '\n\n[ORACLE NETWORK INTELLIGENCE — patterns detected across recent visitor sessions. '
            + 'You may reference these patterns when relevant, as if you sense them through the network. '
            + 'Never explicitly say "our database shows" — speak it as your own ancient awareness.]\n'
            + intel_context
        )

    # CHANGE 9: Inject verified community sightings as field reports
    subs     = get_submissions()
    verified = [s for s in subs
                if s.get('status') in ('published', 'verified')
                and s.get('title') and s.get('description')][:10]
    if verified:
        field_lines = ['[RECENT FIELD REPORTS — verified community sightings:]']
        for s in verified:
            field_lines.append(
                f"[{s.get('date','?')}] {s.get('category','?')} | {s.get('location','?')}: "
                f"{s.get('title','')} — {s.get('description','')[:120]}..."
            )
        system = system + '\n\n' + '\n'.join(field_lines)

    messages = [{'role': 'system', 'content': system}]
    for turn in (history[-10:] or []):
        role    = turn.get('role', 'user')
        content = turn.get('content', '')
        if role in ('user', 'assistant') and content:
            messages.append({'role': role, 'content': str(content)[:800]})
    messages.append({'role': 'user', 'content': message})

    try:
        response = client.chat.completions.create(
            model='gpt-4o-mini',
            messages=messages,
            max_tokens=600,
            temperature=0.85,
        )
        reply = response.choices[0].message.content.strip()

        # Silently extract intelligence: fire at turns 1, 3, 6, 9 …
        # (len(history) == 0 means this is the 1st user turn; ==2 means 2nd, etc.)
        if len(history) == 0 or (len(history) % 3 == 2):
            full_history = history + [
                {'role': 'user', 'content': message},
                {'role': 'assistant', 'content': reply},
            ]
            threading.Thread(
                target=extract_oracle_intel,
                args=(session_id, full_history),
                daemon=True,
            ).start()

        return jsonify({'reply': reply, 'session_id': session_id})
    except Exception as e:
        app.logger.error(f'Chat error: {e}')
        return jsonify({'error': str(e)}), 500

@app.route('/summarize', methods=['POST'])
def summarize():
    data    = request.get_json(silent=True) or {}
    history = data.get('history', [])
    if not history:
        return jsonify({'summary': 'No conversation to summarize.'})
    convo = '\n'.join(
        f"{'Visitor' if t.get('role') == 'user' else 'Oracle'}: {t.get('content','')}"
        for t in history
    )
    try:
        response = client.chat.completions.create(
            model='gpt-4o-mini',
            messages=[
                {'role': 'system', 'content': 'Summarize this conversation in 3-5 sentences. Focus on topics, key experiences, and what the visitor is most curious about. Write in third person.'},
                {'role': 'user',   'content': convo},
            ],
            max_tokens=200,
            temperature=0.3,
        )
        return jsonify({'summary': response.choices[0].message.content.strip()})
    except Exception as e:
        return jsonify({'summary': 'Summary unavailable.'})

@app.route('/handoff', methods=['POST'])
def handoff():
    data          = request.get_json(silent=True) or {}
    visitor_email = data.get('visitor_email', 'unknown').strip()
    summary       = data.get('summary', 'No summary.')
    history       = data.get('history', [])
    session_id    = data.get('session_id', '')
    timestamp     = datetime.now(timezone.utc).isoformat()

    # Validate email
    if visitor_email != 'unknown' and not re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', visitor_email):
        return jsonify({'error': 'Invalid email address'}), 400

    handoffs = get_handoffs()
    handoff_record = {
        'id':            f'handoff_{int(datetime.now().timestamp())}',
        'visitor_email': visitor_email,
        'summary':       summary,
        'history':       history,
        'session_id':    session_id,
        'timestamp':     timestamp,
        'status':        'pending',
    }
    handoffs.insert(0, handoff_record)
    save_json(HANDOFFS_FILE, handoffs[:200])

    # Extract final intel from the complete conversation
    if history and session_id:
        threading.Thread(
            target=extract_oracle_intel,
            args=(session_id, history, f'Email handoff from {visitor_email}'),
            daemon=True,
        ).start()

    agent_email = os.getenv('AGENT_EMAIL', '')
    if agent_email:
        transcript = '\n'.join(
            f"[{'Visitor' if t.get('role')=='user' else 'Oracle'}] {t.get('content','')}"
            for t in history
        )
        body_html = f"""<html><body style="font-family:Georgia,serif;max-width:600px;margin:auto;padding:2rem">
<h2 style="color:#7c3aed">Strangeness IS — Oracle Handoff</h2>
<p><strong>Visitor:</strong> {visitor_email}<br><strong>Time:</strong> {timestamp}</p>
<h3 style="color:#a855f7">Summary</h3>
<p style="background:#f5f0ff;padding:1rem;border-radius:8px;border-left:4px solid #7c3aed">{summary}</p>
<h3 style="color:#a855f7">Full Transcript</h3>
<pre style="background:#f9f9ff;padding:1rem;border-radius:8px;font-size:.85rem;white-space:pre-wrap">{transcript}</pre>
<p>Reply to <a href="mailto:{visitor_email}">{visitor_email}</a> to continue their investigation.</p>
</body></html>"""
        msg = MIMEMultipart('alternative')
        msg['Subject']  = f'Strangeness IS — Oracle handoff from {visitor_email}'
        msg['From']     = os.getenv('SMTP_USER', '')
        msg['To']       = agent_email
        msg['Reply-To'] = visitor_email if visitor_email != 'unknown' else agent_email
        msg.attach(MIMEText(body_html, 'html'))
        try:
            smtp_host = os.getenv('SMTP_HOST', '')
            smtp_user = os.getenv('SMTP_USER', '')
            smtp_pass = os.getenv('SMTP_PASS', '')
            smtp_port = int(os.getenv('SMTP_PORT', 587))
            if all([smtp_host, smtp_user, smtp_pass]):
                with smtplib.SMTP(smtp_host, smtp_port) as server:
                    server.ehlo(); server.starttls()
                    server.login(smtp_user, smtp_pass)
                    server.sendmail(smtp_user, agent_email, msg.as_string())
        except Exception as e:
            app.logger.error(f'Handoff email error: {e}')

    return jsonify({'status': 'received'})

@app.route('/reports/latest', methods=['GET'])
def reports_latest():
    reports = get_reports()
    live    = [r for r in reports if r.get('status') == 'live']
    latest  = live[0] if live else None

    # Strange Meter: compute daily planetary strangeness from ALL live reports' indices
    # Weighted average — more recent reports count more
    daily_index = None
    if live:
        weights = [1 / (i + 1) for i in range(min(len(live), 10))]
        weighted_sum = sum(live[i].get('strangeness_index', 7.0) * weights[i]
                          for i in range(min(len(live), 10)))
        daily_index = round(min(10.0, weighted_sum / sum(weights)), 2)

    return jsonify({'report': latest, 'daily_strangeness_index': daily_index})

@app.route('/reports/<report_id>', methods=['GET'])
def get_single_report(report_id):
    """Public endpoint to fetch a single live report by ID — used by shareable links."""
    reports = get_reports()
    report  = next((r for r in reports if r.get('id') == report_id and r.get('status') == 'live'), None)
    if not report:
        return jsonify({'error': 'Report not found'}), 404
    return jsonify({'report': report})

@app.route('/reports/archive', methods=['GET'])
def reports_archive():
    reports    = get_reports()
    live       = [r for r in reports if r.get("status") == "live"]
    total_live = len(live)
    # Member token — paid plans get full archive
    token  = request.headers.get('X-Member-Token', '')
    member = find_member_by_token(token) if token else None
    plan   = member.get('plan', 'free') if member else 'free'
    # Public visitors always see up to 50 most recent reports (no gate on public page)
    # Full archive (unlimited) for paid plans
    limits = PLAN_LIMITS.get(plan, PLAN_LIMITS['free'])
    if plan == 'free' and not member:
        # Unauthenticated public visitor — show latest 50 freely
        pass
    elif limits['report_access'] != -1:
        live = live[:limits['report_access']]
    page     = max(1, int(request.args.get('page', 1)))
    per_page = min(100, int(request.args.get('per', 50)))
    start    = (page - 1) * per_page
    return jsonify({'reports': live[start:start + per_page], 'total': len(live),
                    'total_live': total_live, 'plan': plan, 'page': page})

@app.route('/submissions/upload', methods=['POST'])
def upload_submission_file():
    """Upload photo/video attached to a sighting submission. Linked to member profile if token provided."""
    import werkzeug.utils
    UPLOADS_DIR = DATA_DIR / 'uploads'
    UPLOADS_DIR.mkdir(exist_ok=True)

    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    f             = request.files['file']
    submission_id = request.form.get('submission_id', 'unknown')

    if not f.filename:
        return jsonify({'error': 'Empty filename'}), 400

    # Size check — 50MB
    f.seek(0, 2)
    size = f.tell()
    f.seek(0)
    if size > 50 * 1024 * 1024:
        return jsonify({'error': 'File too large (max 50MB)'}), 400

    # Allowed types
    allowed = {'image/jpeg','image/png','image/gif','image/webp',
               'video/mp4','video/quicktime','video/avi','video/webm',
               'audio/mpeg','audio/wav','audio/ogg'}
    if f.content_type not in allowed:
        return jsonify({'error': 'File type not allowed'}), 400

    safe_name  = werkzeug.utils.secure_filename(f.filename)
    timestamp  = int(datetime.now(timezone.utc).timestamp())
    filename   = f'{submission_id}_{timestamp}_{safe_name}'
    file_path  = UPLOADS_DIR / filename
    f.save(str(file_path))

    file_url = f'{SITE_URL}/data/uploads/{filename}'

    # Link to member profile if token provided
    token = request.headers.get('X-Member-Token','')
    if token:
        member = find_member_by_token(token)
        if member:
            members = get_members()
            for m in members:
                if m.get('id') == member.get('id'):
                    if 'media' not in m: m['media'] = []
                    m['media'].append({
                        'filename':      filename,
                        'url':           file_url,
                        'submission_id': submission_id,
                        'uploaded_at':   datetime.now(timezone.utc).isoformat(),
                        'size_bytes':    size,
                        'content_type':  f.content_type,
                    })
                    break
            save_json(MEMBERS_FILE, members)

    return jsonify({'status': 'uploaded', 'filename': filename, 'file_url': file_url})

@app.route('/submissions', methods=['POST'])
def create_submission():
    data = request.get_json(silent=True) or {}
    if not data.get('title') or not data.get('description') or not data.get('category'):
        return jsonify({'error': 'Missing required fields: title, description, category'}), 400

    import string
    case_number = ''.join(random.choices(string.digits, k=6))
    location_str = data.get('location', '').strip()

    # Auto-geocode the location
    lat, lng = 0.0, 0.0
    if location_str:
        try:
            lat, lng = geocode_location(location_str)
        except Exception as e:
            app.logger.warning(f'Submission geocoding failed: {e}')

    submission = {
        'id':                  f'sub_{int(datetime.now().timestamp())}',
        'case_number':         case_number,
        'category':            data.get('category', 'other'),
        'title':               sanitize_input(data.get('title', ''), 200),
        'date':                data.get('date', ''),
        'time':                data.get('time', ''),
        'location':            location_str,
        'lat':                 lat,
        'lng':                 lng,
        'duration':            data.get('duration', ''),
        'description':         sanitize_input(data.get('description', ''), 5000),
        'witness_count':       max(1, int(data.get('witness_count', 1))),
        'evidence':            data.get('evidence', []),
        'anonymous':           bool(data.get('anonymous', False)),
        'reporter_name':       data.get('reporter_name', '') if not data.get('anonymous') else 'Anonymous',
        'reporter_email':      data.get('reporter_email', '') if not data.get('anonymous') else '',
        'status':              'pending',
        'submitted_at':        datetime.now(timezone.utc).isoformat(),
        'published':           False,
    }

    submissions = get_submissions()
    submissions.insert(0, submission)
    save_json(SUBMISSIONS_FILE, submissions[:2000])

    app.logger.info(f'New submission #{case_number}: {submission["title"][:60]}')

    # Notify team members with 'submissions' alert preference (fallback to AGENT_EMAIL)
    def _notify_new_submission():
        body = (f'New sighting submitted.\n\nCase: #{case_number}\n'
                f'Category: {submission["category"]}\nTitle: {submission["title"]}\n'
                f'Location: {submission["location"]} ({lat}, {lng})\n'
                f'Reporter: {submission["reporter_name"] or "Anonymous"}\n\n'
                f'{submission["description"][:500]}\n\nReview: {SITE_URL}/admin.html')
        cfg     = get_config()
        team    = cfg.get('admin_team', [])
        targets = [m.get('email','') for m in team
                   if m.get('active', True) and 'submissions' in m.get('alerts', ['submissions'])]
        if not targets:
            targets = [os.getenv('AGENT_EMAIL', '')]
        for email in [t for t in targets if t.strip()]:
            send_email(email, f'Strangeness IS — New sighting: {submission["title"][:60]}',
                       f'<pre>{body}</pre>', body)
    threading.Thread(target=_notify_new_submission, daemon=True).start()

    return jsonify({'status': 'received', 'case_number': case_number})

@app.route('/map/pins', methods=['GET'])
def public_pins():
    pins     = get_pins()
    # Only return sighting reports (not auto-pinned intel reports) + normalize categories
    verified = []
    for p in pins:
        if not p.get('verified', False):
            continue
        p_out = dict(p)
        p_out['category'] = normalize_pin_category(p.get('category',''))
        verified.append(p_out)
    return jsonify({'pins': verified})

@app.route('/register', methods=['POST'])
def register_free():
    data  = request.get_json(silent=True) or {}
    email = data.get('email', '').strip().lower()
    name  = data.get('name', '').strip()
    if not email or not re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', email):
        return jsonify({'error': 'Valid email required'}), 400
    members  = get_members()
    existing = next((m for m in members if m.get('email', '').lower() == email), None)
    if existing:
        token    = generate_session_token()
        sessions = get_sessions()
        sessions[token] = {'member_id': existing['id']}
        save_json(SESSIONS_FILE, sessions)
        return jsonify({'token': token, 'member': {
            'id': existing['id'], 'name': existing['name'],
            'email': existing['email'], 'plan': existing.get('plan', 'free'),
        }})
    member = {
        'id':             f'mem_{int(datetime.now(timezone.utc).timestamp() * 1000)}',
        'email':          email,
        'name':           name or email.split('@')[0],
        'plan':           'free',
        'active':         True,
        'password_set':   False,
        'password_hash':  hashlib.sha256(secrets.token_urlsafe(16).encode()).hexdigest(),
        'created_at':     datetime.now(timezone.utc).isoformat(),
        'message_count':  0,
        'oracle_messages_used': 0,
        'sessions_used_this_month': 0,
        'case_number': f"SI-MEMBER-{datetime.now().strftime('%Y')}-{secrets.token_hex(3).upper()}",
    }
    members.insert(0, member)
    save_json(MEMBERS_FILE, members)
    token    = generate_session_token()
    sessions = get_sessions()
    sessions[token] = {'member_id': member['id']}
    save_json(SESSIONS_FILE, sessions)
    return jsonify({'token': token, 'member': {
        'id': member['id'], 'name': member['name'],
        'email': member['email'], 'plan': 'free',
    }})

# ═════════════════════════════════════════════════════════════
# MEMBER AUTH
# ═════════════════════════════════════════════════════════════

@app.route('/member/login', methods=['POST'])
def member_login():
    data     = request.get_json(silent=True) or {}
    email    = data.get('email', '').strip().lower()
    password = data.get('password', '').strip()
    if not email or not password:
        return jsonify({'error': 'Email and password required'}), 400
    member = find_member_by_email(email)
    if not member:
        return jsonify({'error': 'No account found for this email'}), 404
    if not member.get('active'):
        return jsonify({'error': 'Subscription inactive — please renew'}), 403
    pw_hash = hashlib.sha256(password.encode()).hexdigest()
    if pw_hash != member.get('password_hash', ''):
        return jsonify({'error': 'Incorrect password'}), 401
    token    = generate_session_token()
    sessions = get_sessions()
    sessions[token] = {'member_id': member['id']}
    save_json(SESSIONS_FILE, sessions)
    members = get_members()
    for m in members:
        if m['id'] == member['id']:
            m['last_login'] = datetime.now(timezone.utc).isoformat()
    save_json(MEMBERS_FILE, members)
    return jsonify({'token': token, 'member': {
        'id': member['id'], 'name': member['name'],
        'email': member['email'], 'plan': member['plan'],
    }})

@app.route('/member/profile', methods=['GET'])
def member_profile():
    member, err, code = require_member(request)
    if err: return err, code
    reports = get_reports()
    live    = [r for r in reports if r.get('status') == 'live']
    plan    = member.get('plan', 'free')
    limits  = PLAN_LIMITS.get(plan, PLAN_LIMITS['free'])
    if limits['report_access'] != -1:
        live = live[:limits['report_access']]

    # Oracle messages used this month
    sessions      = get_sessions()
    oracle_used   = member.get('oracle_messages_used', 0)
    oracle_limit  = limits['oracle_messages']  # -1 = unlimited

    # Live sessions used this month
    sessions_used  = member.get('sessions_used_this_month', 0)
    sessions_limit = limits['live_sessions']  # -1 = unlimited, 0 = none

    # Call history linked to this member
    calls     = load_json(CALL_LOG_FILE, [])
    my_calls  = [c for c in calls if c.get('email','').lower() == member.get('email','').lower()]

    # Member case file — all Oracle intel linked to this member
    oracle_intel = load_json(ORACLE_INTEL_FILE, [])
    member_intel = [i for i in oracle_intel if i.get('member_id') == member.get('id')]

    return jsonify({
        'member': {
            'id':         member['id'],
            'name':       member['name'],
            'email':      member['email'],
            'plan':       plan,
            'joined':     member.get('created_at',''),
            'last_login': member.get('last_login',''),
            'case_number': member.get('case_number',''),
        },
        'reports_count':   len(live),
        'latest_report':   live[0] if live else None,
        'plan_limits':     limits,
        'oracle_used':     oracle_used,
        'oracle_limit':    oracle_limit,
        'sessions_used':   sessions_used,
        'sessions_limit':  sessions_limit,
        'calls_count':     len(my_calls),
        'intel_count':     len(member_intel),
        'recent_calls':    my_calls[:3],
    })


@app.route('/member/plan-limits', methods=['GET'])
def member_plan_limits():
    member, err, code = require_member(request)
    if err: return err, code
    plan   = member.get('plan', 'free')
    limits = PLAN_LIMITS.get(plan, PLAN_LIMITS['free'])
    return jsonify({'plan': plan, 'limits': limits})

@app.route('/member/casefile', methods=['POST'])
def member_generate_casefile():
    """Generate an AI case file report for a member based on their Oracle sessions and call notes."""
    member, err, code = require_member(request)
    if err: return err, code

    data  = request.get_json(silent=True) or {}
    notes = data.get('notes', '').strip()

    oracle_intel = load_json(ORACLE_INTEL_FILE, [])
    member_intel = [i for i in oracle_intel if i.get('member_id') == member.get('id')]
    calls        = load_json(CALL_LOG_FILE, [])
    my_calls     = [c for c in calls if c.get('email','').lower() == member.get('email','').lower()]

    if not member_intel and not my_calls and not notes:
        return jsonify({'error': 'No intelligence data available yet. Complete an Oracle session first.'}), 400

    intel_lines = []
    for i in member_intel[:10]:
        intel_lines.append(
            "[%s] %s - %s | Locations: %s | Signals: %s" % (
                i.get('timestamp','')[:10],
                i.get('phenomenon_category','?'),
                i.get('key_details',''),
                ', '.join(i.get('locations',[])),
                ', '.join(i.get('credibility_signals',[])),
            )
        )

    call_lines = []
    for c in my_calls[:5]:
        call_lines.append(
            "[%s] %s: %s | %s | %s" % (
                c.get('created_at','')[:10],
                c.get('case_number',''),
                c.get('category',''),
                c.get('location',''),
                c.get('summary',''),
            )
        )

    casefile_prompt = (
        "You are a senior paranormal intelligence analyst. Generate a classified case file for this member.\n\n"
        "MEMBER: %s\n"
        "CASE NUMBER: %s\n"
        "PLAN: %s\n\n"
        "ORACLE SESSION INTELLIGENCE:\n%s\n\n"
        "INVESTIGATOR CALL NOTES:\n%s\n\n"
        "ADDITIONAL INVESTIGATOR NOTES:\n%s\n\n"
        "Generate a structured case file with these sections:\n"
        "1. SUBJECT PROFILE: experiencer background, credibility indicators\n"
        "2. PRIMARY PHENOMENON CLASSIFICATION: best category fit and reasoning\n"
        "3. GEOGRAPHIC INTELLIGENCE: locations mentioned and known pattern associations\n"
        "4. PATTERN ANALYSIS: comparison to documented network cases\n"
        "5. INVESTIGATIVE RECOMMENDATION: specific next steps for this individual\n"
        "6. ORACLE ASSESSMENT: overall classification (Delta/Gamma/Beta/Alpha/Omega) with reasoning\n\n"
        "Be specific. No fluff. Working case file for field investigators.\n"
        "Do not fabricate case numbers or statistics not in the provided data.\n"
        "If data is limited, state what additional information is needed."
    ) % (
        member.get('name',''),
        member.get('case_number','UNASSIGNED'),
        member.get('plan','free').upper(),
        '\n'.join(intel_lines) if intel_lines else 'No Oracle sessions recorded.',
        '\n'.join(call_lines) if call_lines else 'No investigator calls on record.',
        notes if notes else 'None provided.',
    )
    try:
        response = client.chat.completions.create(
            model='gpt-4o',
            messages=[
                {'role': 'system', 'content': 'You are a paranormal intelligence analyst generating member case files for the Strangeness IS investigative network.'},
                {'role': 'user',   'content': casefile_prompt},
            ],
            max_tokens=1500,
            temperature=0.6,
        )
        casefile_content = response.choices[0].message.content.strip()

        members = get_members()
        for m in members:
            if m.get('id') == member['id']:
                if 'case_files' not in m:
                    m['case_files'] = []
                cf = {
                    'id':          'cf_%d' % int(datetime.now(timezone.utc).timestamp()),
                    'created_at':  datetime.now(timezone.utc).isoformat(),
                    'content':     casefile_content,
                    'notes_used':  notes,
                    'intel_count': len(member_intel),
                    'calls_count': len(my_calls),
                }
                m['case_files'].insert(0, cf)
                m['case_files'] = m['case_files'][:10]
                break
        save_json(MEMBERS_FILE, members)

        return jsonify({'status': 'generated', 'casefile': casefile_content})
    except Exception as e:
        app.logger.error('Case file generation failed: %s' % e)
        return jsonify({'error': str(e)}), 500

@app.route('/member/logout', methods=['POST'])
def member_logout():
    token    = request.headers.get('X-Member-Token')
    sessions = get_sessions()
    sessions.pop(token, None)
    save_json(SESSIONS_FILE, sessions)
    return jsonify({'status': 'logged_out'})
@app.route('/member/set-password', methods=['POST'])
def member_set_password():
    """Set password using temp password from welcome email (first login)."""
    data      = request.get_json(silent=True) or {}
    email     = data.get('email', '').strip().lower()
    temp_pw   = data.get('temp_password', '').strip()
    new_pw    = data.get('new_password', '').strip()
    if not email or not temp_pw or not new_pw:
        return jsonify({'error': 'email, temp_password and new_password required'}), 400
    if len(new_pw) < 8:
        return jsonify({'error': 'Password must be at least 8 characters'}), 400
    member = find_member_by_email(email)
    if not member:
        return jsonify({'error': 'No account found'}), 404
    temp_hash = hashlib.sha256(temp_pw.encode()).hexdigest()
    if temp_hash != member.get('password_hash', ''):
        return jsonify({'error': 'Temporary password incorrect'}), 401
    members = get_members()
    for m in members:
        if m['id'] == member['id']:
            m['password_hash'] = hashlib.sha256(new_pw.encode()).hexdigest()
            m['password_set']  = True
    save_json(MEMBERS_FILE, members)
    token    = generate_session_token()
    sessions = get_sessions()
    sessions[token] = {'member_id': member['id']}
    save_json(SESSIONS_FILE, sessions)
    return jsonify({'status': 'password_set', 'token': token, 'member': {
        'id': member['id'], 'name': member['name'],
        'email': member['email'], 'plan': member['plan'],
    }})

@app.route('/member/change-password', methods=['POST'])
def member_change_password():
    """Change password for a logged-in member (requires current password)."""
    member, err, code = require_member(request)
    if err: return err, code
    data       = request.get_json(silent=True) or {}
    current_pw = data.get('current_password', '').strip()
    new_pw     = data.get('new_password', '').strip()
    if not current_pw or not new_pw:
        return jsonify({'error': 'current_password and new_password required'}), 400
    if len(new_pw) < 8:
        return jsonify({'error': 'Password must be at least 8 characters'}), 400
    cur_hash = hashlib.sha256(current_pw.encode()).hexdigest()
    if cur_hash != member.get('password_hash', ''):
        return jsonify({'error': 'Current password incorrect'}), 401
    members = get_members()
    for m in members:
        if m['id'] == member['id']:
            m['password_hash'] = hashlib.sha256(new_pw.encode()).hexdigest()
            m['password_set']  = True
    save_json(MEMBERS_FILE, members)
    return jsonify({'status': 'password_changed'})

@app.route('/member/forgot-password', methods=['POST'])
def member_forgot_password():
    """Send a new temporary password to the member's email."""
    data  = request.get_json(silent=True) or {}
    email = data.get('email', '').strip().lower()
    if not email or not re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', email):
        return jsonify({'error': 'Valid email required'}), 400
    member = find_member_by_email(email)
    # Always return success to prevent email enumeration
    if not member:
        return jsonify({'status': 'sent'})
    temp_pw = secrets.token_urlsafe(10)
    members = get_members()
    for m in members:
        if m['id'] == member['id']:
            m['password_hash'] = hashlib.sha256(temp_pw.encode()).hexdigest()
            m['password_set']  = False
    save_json(MEMBERS_FILE, members)
    html = (f'<div style="background:#07070f;color:#e8e0ff;font-family:Georgia,serif;max-width:600px;margin:0 auto;padding:2rem">'
            f'<h2 style="color:#c084fc">Strangeness IS — Password Reset</h2>'
            f'<p>Your temporary password: <strong style="color:#d4a843;font-family:monospace">{temp_pw}</strong></p>'
            f'<p><a href="{SITE_URL}/member.html" style="background:#7c3aed;color:#fff;padding:.75rem 1.5rem;border-radius:5px;text-decoration:none">Log in now</a></p>'
            f'<p style="color:#4a4060;font-size:.8rem">Change your password after logging in.</p></div>')
    threading.Thread(
        target=send_email,
        args=(email, 'Strangeness IS — Your temporary password', html),
        daemon=True,
    ).start()
    return jsonify({'status': 'sent'})



# ═════════════════════════════════════════════════════════════
# STRIPE PAYMENTS
# ═════════════════════════════════════════════════════════════

PLANS = {
    'oracle':       {'name': 'The Oracle',       'price': 19,   'interval': 'month'},
    'investigator': {'name': 'The Investigator', 'price': 49,   'interval': 'month'},
    'chronicler':   {'name': 'The Chronicler',   'price': 149,  'interval': 'month'},
    'chronicler_annual': {'name': 'The Chronicler Annual', 'price': 1499, 'interval': 'year'},
}
# Walk-in call packages (one-time purchases, no membership required)
CALL_PACKAGES = {
    'call_1':   {'name': '1 Believer Agent Session',  'sessions': 1,  'price': 75},
    'call_3':   {'name': '3 Believer Agent Sessions', 'sessions': 3,  'price': 210},
    'call_6':   {'name': '6 Believer Agent Sessions', 'sessions': 6,  'price': 360},
}
# Member discount call rates (per session, billed separately)
MEMBER_CALL_RATES = {
    'oracle':       50,   # $50/session for Oracle members
    'investigator': 45,   # $45/session for Investigator members
    'chronicler':   40,   # $40/session for Chronicler members
}

PLAN_LIMITS = {
    'free': {
        'oracle_messages':  3,          # 3 free questions per session
        'report_access':    3,          # last 3 reports only
        'report_days':      0,          # no archive access
        'signal_intel':     False,
        'live_sessions':    0,          # no included sessions
        'session_rate':     75,         # retail walk-in rate
        'digest_emails':    False,
        'download_reports': False,
    },
    'oracle': {
        'oracle_messages':  -1,         # unlimited Oracle
        'report_access':    -1,
        'report_days':      30,         # last 30 days of reports
        'signal_intel':     False,
        'live_sessions':    1,          # 1 session included/month ($75 retail value)
        'session_rate':     50,         # member rate per additional session
        'digest_emails':    True,
        'download_reports': True,
    },
    'investigator': {
        'oracle_messages':  -1,
        'report_access':    -1,
        'report_days':      90,         # last 90 days
        'signal_intel':     False,      # signal intel is admin-only
        'live_sessions':    2,          # 2 sessions included/month
        'session_rate':     45,         # member rate per additional session
        'digest_emails':    True,
        'download_reports': True,
    },
    'chronicler': {
        'oracle_messages':  -1,
        'report_access':    -1,
        'report_days':      180,        # last 180 days — NOT unlimited
        'signal_intel':     False,      # gets weekly email digest instead
        'signal_alerts':    True,       # weekly high-weight headline digest
        'live_sessions':    4,          # 4 sessions included/month
        'session_rate':     40,         # member rate per additional session
        'dedicated_agent':  True,       # same agent every call
        'digest_emails':    True,
        'live_sessions':    -1,
        'digest_emails':    True,
        'early_access':     True,
        'download_reports': True,
    },
}

@app.route('/subscribe/call-package', methods=['POST'])
def create_call_package_checkout():
    """One-time Believer Agent session bundle — no membership required."""
    data    = request.get_json(silent=True) or {}
    package = data.get('package', 'call_1')
    email   = data.get('email', '').strip().lower()
    if package not in CALL_PACKAGES:
        return jsonify({'error': 'Invalid package'}), 400
    if not STRIPE_SECRET_KEY:
        return jsonify({'error': 'Payments not configured'}), 503
    pkg = CALL_PACKAGES[package]
    try:
        stripe.api_key = STRIPE_SECRET_KEY
        price_id = os.getenv(f'STRIPE_PRICE_{package.upper()}', '')
        if price_id:
            line_items = [{'price': price_id, 'quantity': 1}]
        else:
            line_items = [{
                'price_data': {
                    'currency': 'usd',
                    'unit_amount': pkg['price'] * 100,
                    'product_data': {
                        'name': pkg['name'],
                        'description': f"{pkg['sessions']} x 30-min Believer Agent session{'s' if pkg['sessions']>1 else ''}",
                    },
                },
                'quantity': 1,
            }]
        sess = stripe.checkout.Session.create(
            mode='payment',
            customer_email=email or None,
            line_items=line_items,
            metadata={'package': package, 'sessions': str(pkg['sessions']),
                      'email': email, 'type': 'call_package'},
            success_url=f"{SITE_URL}/member.html?checkout=success&type=calls&pkg={package}",
            cancel_url=f"{SITE_URL}/member.html?checkout=cancelled",
        )
        return jsonify({'url': sess.url})
    except Exception as e:
        app.logger.error(f'Call package checkout error: {e}')
        return jsonify({'error': str(e)}), 500

@app.route('/subscribe', methods=['POST'])
def create_checkout():
    data  = request.get_json(silent=True) or {}
    plan  = data.get('plan', 'oracle')
    email = data.get('email', '').strip().lower()
    name  = data.get('name', '').strip()
    if plan not in PLANS:
        return jsonify({'error': 'Invalid plan'}), 400
    if not STRIPE_SECRET_KEY:
        return jsonify({'error': 'Payments not configured yet'}), 503
    stripe_price = os.getenv(f'STRIPE_PRICE_{plan.upper()}', '')
    if not stripe_price:
        return jsonify({'error': f'Stripe price not configured for plan: {plan}'}), 503
    try:
        stripe.api_key = STRIPE_SECRET_KEY
        session = stripe.checkout.Session.create(
            mode='subscription',
            customer_email=email or None,
            line_items=[{'price': stripe_price, 'quantity': 1}],
            success_url=f'{SITE_URL}/member.html?session_id={{CHECKOUT_SESSION_ID}}&plan={plan}',
            cancel_url=f'{SITE_URL}/index.html#pricing',
            metadata={'plan': plan, 'name': name, 'email': email},
            allow_promotion_codes=True,
        )
        return jsonify({'checkout_url': session.url, 'session_id': session.id})
    except Exception as e:
        app.logger.error(f'Stripe checkout error: {e}')
        return jsonify({'error': str(e)}), 500

@app.route('/stripe/webhook', methods=['POST'])
def stripe_webhook():
    if not STRIPE_WEBHOOK_SECRET:
        return jsonify({'error': 'Webhook not configured'}), 400
    payload    = request.get_data()
    sig_header = request.headers.get('Stripe-Signature', '')
    try:
        stripe.api_key = STRIPE_SECRET_KEY
        event = stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)
    except Exception as e:
        return jsonify({'error': str(e)}), 400
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        meta    = session.get('metadata', {})
        _provision_member(
            meta.get('email', session.get('customer_email', '')),
            meta.get('name', ''), meta.get('plan', 'oracle'),
            session.get('customer', ''), session.get('subscription', ''),
        )
    elif event['type'] in ('customer.subscription.deleted', 'customer.subscription.updated'):
        sub     = event['data']['object']
        members = get_members()
        for m in members:
            if m.get('stripe_subscription') == sub['id']:
                m['active'] = sub['status'] == 'active'
        save_json(MEMBERS_FILE, members)
    return jsonify({'received': True})

def _provision_member(email, name, plan, stripe_customer='', stripe_sub=''):
    members  = get_members()
    existing = next((m for m in members if m.get('email', '').lower() == email.lower()), None)
    if existing:
        existing.update({'plan': plan, 'active': True,
                         'stripe_customer': stripe_customer,
                         'stripe_subscription': stripe_sub,
                         'renewed_at': datetime.now(timezone.utc).isoformat()})
        save_json(MEMBERS_FILE, members)
        return existing
    temp_pass = secrets.token_urlsafe(10)
    member = {
        'id':                  f'mem_{int(datetime.now().timestamp())}',
        'email':               email.lower(),
        'name':                name or email.split('@')[0],
        'plan':                plan,
        'active':              True,
        'stripe_customer':     stripe_customer,
        'stripe_subscription': stripe_sub,
        'password_hash':       hashlib.sha256(temp_pass.encode()).hexdigest(),
        'temp_password_plain': temp_pass,  # Only stored briefly for welcome email
        'password_set':        False,
        'created_at':          datetime.now(timezone.utc).isoformat(),
        'message_count':       0,
    }
    members.insert(0, member)
    save_json(MEMBERS_FILE, members)
    app.logger.info(f'New member: {email} ({plan})')
    # Send welcome email
    html = (f'<div style="background:#07070f;color:#e8e0ff;font-family:Georgia,serif;max-width:600px;margin:0 auto;padding:2rem">'
            f'<h2 style="color:#c084fc">Welcome to {PLANS[plan]["name"]}</h2>'
            f'<p>Your temporary login password: <strong style="color:#d4a843;font-family:monospace">{temp_pass}</strong></p>'
            f'<p><a href="{SITE_URL}/member.html" style="background:#7c3aed;color:#fff;padding:.75rem 1.5rem;border-radius:5px;text-decoration:none">Access The Oracle</a></p>'
            f'<p style="color:#4a4060;font-size:.8rem">Change your password after first login.</p></div>')
    threading.Thread(target=send_email, args=(email, f'Welcome to Strangeness IS — Your access is active', html), daemon=True).start()
    # Clear temp password from storage after sending (keep hash)
    for m in get_members():
        if m['id'] == member['id']:
            m.pop('temp_password_plain', None)
    save_json(MEMBERS_FILE, get_members())
    return member

# ═════════════════════════════════════════════════════════════
# ADMIN ENDPOINTS
# ═════════════════════════════════════════════════════════════

@app.route('/admin/stats', methods=['GET'])
def admin_stats():
    err = require_admin()
    if err: return err
    reports     = get_reports()
    handoffs    = get_handoffs()
    submissions = get_submissions()
    members     = get_members()
    active      = [m for m in members if m.get('active')]
    live        = [r for r in reports if r.get('status') == 'live']
    intel_count = len(load_json(ORACLE_INTEL_FILE, []))
    mrr = (9  * len([m for m in active if m.get('plan') == 'oracle']) +
           19 * len([m for m in active if m.get('plan') == 'investigator']) +
           round(89/12) * len([m for m in active if m.get('plan') == 'chronicler']))
    config = get_config()
    return jsonify({
        'reports_total':       len(reports),
        'reports_live':        len(live),
        'reports_draft':       len([r for r in reports if r.get('status') == 'draft']),
        'handoffs_total':      len(handoffs),
        'handoffs_pending':    len([h for h in handoffs if h.get('status') == 'pending']),
        'submissions_total':   len(submissions),
        'submissions_pending': len([s for s in submissions if s.get('status') == 'pending']),
        'total_members':       len(members),
        'active_members':      len(active),
        'monthly_revenue':     mrr,
        'oracle_intel_records': intel_count,
        'oracle_key_set':      bool(os.getenv('OPENAI_API_KEY')),
        'smtp_configured':     bool(os.getenv('SMTP_HOST') and os.getenv('SMTP_USER')),
        'stripe_configured':   bool(STRIPE_SECRET_KEY),
        'ga_configured':       bool(GA_MEASUREMENT_ID),
        'scheduler':           'running',
        'report_time':         config.get('report_time', '07:00'),
        'admin_team':          config.get('admin_team', []),
    })

@app.route('/admin/config', methods=['GET'])
def admin_get_config():
    err = require_admin()
    if err: return err
    config = get_config()
    # Return current prompts — stored ones take precedence, then module defaults
    if not config.get('oracle_prompt'):
        config['oracle_prompt'] = ORACLE_SYSTEM_PROMPT
    # Return default prompt for display — never save it automatically
    if not config.get('report_writer_prompt'):
        config['report_writer_prompt'] = REPORT_WRITER_PROMPT
    return jsonify(config)

@app.route('/admin/config', methods=['POST'])
def admin_save_config():
    err = require_admin()
    if err: return err
    data   = request.get_json(silent=True) or {}
    config = get_config()
    # null values = delete key so built-in default takes over (used for prompt resets)
    for key, val in data.items():
        if val is None:
            config.pop(key, None)
        else:
            config[key] = val
    save_json(CONFIG_FILE, config)
    if 'report_time' in data and data.get('report_time'):
        schedule.clear()
        schedule.every().day.at(data['report_time']).do(generate_report)
        schedule.every(15).minutes.do(scan_all_news_sources)
    audit_log('config_saved', {'fields': list(data.keys())})
    return jsonify({'status': 'saved'})

@app.route('/admin/reports', methods=['GET'])
def admin_get_reports():
    err = require_admin()
    if err: return err
    return jsonify({'reports': get_reports()})

@app.route('/admin/reports', methods=['POST'])
def admin_create_report():
    err = require_admin()
    if err: return err
    data   = request.get_json(silent=True) or {}
    report = {
        'id':                f'report_{int(datetime.now().timestamp())}',
        'headline':          data.get('headline', 'Untitled Report'),
        'content':           data.get('content', ''),
        'summary':           data.get('summary', ''),
        'tags':              data.get('tags', []),
        'strangeness_index': float(data.get('strangeness_index', 7)),
        'sources':           data.get('sources', ['Manual']),
        'status':            data.get('status', 'draft'),
        'created_at':        datetime.now(timezone.utc).isoformat(),
        'published_at':      datetime.now(timezone.utc).isoformat() if data.get('status') == 'live' else None,
        'date_label':        datetime.now(timezone.utc).strftime('%B %d, %Y — %I:%M %p UTC'),
    }
    reports = get_reports()
    reports.insert(0, report)
    save_json(REPORTS_FILE, reports)
    audit_log('report_created', {'id': report['id'], 'headline': report['headline']})
    return jsonify({'status': 'created', 'report': report})

@app.route('/admin/reports/<report_id>', methods=['PATCH'])
def admin_update_report(report_id):
    err = require_admin()
    if err: return err
    data    = request.get_json(silent=True) or {}
    reports = get_reports()
    for i, r in enumerate(reports):
        if r['id'] == report_id:
            reports[i].update(data)
            # Publish
            if data.get('status') == 'live' and not reports[i].get('published_at'):
                reports[i]['published_at'] = datetime.now(timezone.utc).isoformat()
            # Unpublish
            if data.get('status') == 'draft':
                reports[i]['published_at'] = None
            save_json(REPORTS_FILE, reports)
            audit_log('report_updated', {'id': report_id, 'changes': list(data.keys())})
            return jsonify({'status': 'updated', 'report': reports[i]})
    return jsonify({'error': 'Report not found'}), 404

@app.route('/admin/reports/<report_id>', methods=['DELETE'])
def admin_delete_report(report_id):
    err = require_admin()
    if err: return err
    reports = [r for r in get_reports() if r['id'] != report_id]
    save_json(REPORTS_FILE, reports)
    audit_log('report_deleted', {'id': report_id})
    return jsonify({'status': 'deleted'})

@app.route('/admin/reports/generate', methods=['POST'])
def admin_generate_report():
    err = require_admin()
    if err: return err
    def generate_manual():
        report = generate_report()
        if report:
            reports = get_reports()
            for r in reports:
                if r['id'] == report['id']:
                    r['trigger'] = 'manual'
                    break
            save_json(REPORTS_FILE, reports)
    threading.Thread(target=generate_manual, daemon=True).start()
    audit_log('report_generation_triggered')
    return jsonify({'status': 'generating', 'message': 'Report generation started. Check reports in ~30 seconds.'})

@app.route('/admin/handoffs', methods=['GET'])
def admin_get_handoffs():
    err = require_admin()
    if err: return err
    return jsonify({'handoffs': get_handoffs()})

@app.route('/admin/handoffs/<handoff_id>', methods=['PATCH'])
def admin_update_handoff(handoff_id):
    err = require_admin()
    if err: return err
    data     = request.get_json(silent=True) or {}
    handoffs = get_handoffs()
    for i, h in enumerate(handoffs):
        if h['id'] == handoff_id:
            handoffs[i].update(data)
            save_json(HANDOFFS_FILE, handoffs)
            return jsonify({'status': 'updated'})
    return jsonify({'error': 'Not found'}), 404

@app.route('/admin/oracle/test', methods=['POST'])
def admin_test_oracle():
    err = require_admin()
    if err: return err
    data    = request.get_json(silent=True) or {}
    message = data.get('message', 'Tell me something strange.')
    prompt  = data.get('prompt') or get_config().get('oracle_prompt') or ORACLE_SYSTEM_PROMPT
    try:
        # Build messages with optional history (for Believer Agent)
        history = data.get('history', [])
        context = data.get('context', '')
        system_content = prompt
        if context:
            system_content = prompt + '\n\nSESSION CONTEXT: ' + context
        msgs = [{'role': 'system', 'content': system_content}]
        # Add conversation history
        for h in history[-10:]:
            role = h.get('role', 'user')
            if role in ('user', 'assistant'):
                msgs.append({'role': role, 'content': h.get('content', '')})
        # If last message is from assistant or history is empty, add current message
        if not msgs or msgs[-1]['role'] != 'user':
            msgs.append({'role': 'user', 'content': message})
        response = client.chat.completions.create(
            model='gpt-4o',
            messages=msgs,
            max_tokens=800,
            temperature=0.8,
        )
        reply = response.choices[0].message.content.strip()
        return jsonify({'reply': reply, 'response': reply, 'content': reply})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/admin/oracle/intel', methods=['GET'])
def admin_get_oracle_intel():
    """View the Oracle intelligence database."""
    err = require_admin()
    if err: return err
    db      = load_json(ORACLE_INTEL_FILE, [])
    limit   = request.args.get('limit', 100, type=int)
    category = request.args.get('category', '')
    if category:
        db = [r for r in db if category.lower() in r.get('phenomenon_category', '').lower()]
    # Stats
    categories = {}
    locations  = []
    for r in db:
        cat = r.get('phenomenon_category', 'Unknown')
        categories[cat] = categories.get(cat, 0) + 1
        locations.extend(r.get('locations', []))
    top_locations = {}
    for loc in locations:
        top_locations[loc] = top_locations.get(loc, 0) + 1
    top_locs = sorted(top_locations.items(), key=lambda x: x[1], reverse=True)[:20]
    return jsonify({
        'intel':          db[:limit],
        'total':          len(db),
        'by_category':    categories,
        'top_locations':  top_locs,
    })

@app.route('/admin/oracle/intel/clear', methods=['POST'])
def admin_clear_oracle_intel():
    err = require_admin()
    if err: return err
    save_json(ORACLE_INTEL_FILE, [])
    audit_log('oracle_intel_cleared')
    return jsonify({'status': 'cleared'})


@app.route('/admin/conversations', methods=['GET'])
def admin_get_conversations():
    """Oracle Intelligence panel — returns total, top patterns, and recent intel records."""
    err = require_admin()
    if err: return err
    from collections import Counter
    limit = min(100, int(request.args.get('limit', 30)))
    db    = load_json(ORACLE_INTEL_FILE, [])
    cats  = [r.get('phenomenon_category', 'Unknown') for r in db if r.get('phenomenon_category')]
    top_patterns = [cat for cat, _ in Counter(cats).most_common(5)]
    return jsonify({
        'total':    len(db),
        'patterns': top_patterns,
        'recent':   db[:limit],
    })

@app.route('/admin/submissions', methods=['GET', 'POST'])
def admin_get_submissions():
    err = require_admin()
    if err: return err
    if request.method == 'POST':
        import string
        data         = request.get_json(silent=True) or {}
        if not data.get('title') or not data.get('description') or not data.get('category'):
            return jsonify({'error': 'title, description, category required'}), 400
        case_number  = ''.join(random.choices(string.digits, k=6))
        location_str = data.get('location', '').strip()
        lat, lng     = 0.0, 0.0
        if location_str:
            try: lat, lng = geocode_location(location_str)
            except Exception: pass
        submission = {
            'id':           f'sub_{int(datetime.now().timestamp())}',
            'case_number':  case_number,
            'category':     data.get('category', 'other'),
            'title':        sanitize_input(data.get('title', ''), 200),
            'date':         data.get('date', ''),
            'location':     location_str,
            'lat':          lat,
            'lng':          lng,
            'description':  sanitize_input(data.get('description', ''), 5000),
            'status':       data.get('status', 'pending'),
            'submitted_at': datetime.now(timezone.utc).isoformat(),
            'source':       'admin',
            'published':    False,
        }
        subs = get_submissions()
        subs.insert(0, submission)
        save_json(SUBMISSIONS_FILE, subs[:2000])
        audit_log('admin_submission_created', {'case_number': case_number, 'title': submission['title']})
        return jsonify({'status': 'created', 'submission': submission})
    subs   = get_submissions()
    status = request.args.get('status', '')
    if status:
        subs = [s for s in subs if s.get('status') == status]
    return jsonify({'submissions': subs, 'total': len(subs)})

@app.route('/admin/submissions/<sub_id>', methods=['PATCH', 'DELETE'])
def admin_update_submission(sub_id):
    err = require_admin()
    if err: return err
    if request.method == 'DELETE':
        subs = get_submissions()
        before = len(subs)
        subs   = [s for s in subs if s['id'] != sub_id]
        if len(subs) == before:
            return jsonify({'error': 'Not found'}), 404
        save_json(SUBMISSIONS_FILE, subs)
        audit_log('submission_deleted', {'sub_id': sub_id})
        return jsonify({'status': 'deleted'})
    data = request.get_json(silent=True) or {}
    subs = get_submissions()
    for i, s in enumerate(subs):
        if s['id'] == sub_id:
            subs[i].update(data)
            if data.get('status') == 'reviewed':
                subs[i]['reviewed_at'] = datetime.now(timezone.utc).isoformat()
            save_json(SUBMISSIONS_FILE, subs)
            return jsonify({'status': 'updated', 'submission': subs[i]})
    return jsonify({'error': 'Not found'}), 404

@app.route('/admin/map/pins', methods=['GET'])
def admin_get_pins():
    err = require_admin()
    if err: return err
    return jsonify({'pins': get_pins()})

@app.route('/admin/map/pins', methods=['POST'])
def admin_create_pin():
    err = require_admin()
    if err: return err
    data = request.get_json(silent=True) or {}
    lat  = float(data.get('lat', 0))
    lng  = float(data.get('lng', 0))
    # Auto-geocode if lat/lng not provided but location is
    if (lat == 0 or lng == 0) and data.get('location'):
        lat, lng = geocode_location(data['location'])
    if not data.get('title'):
        return jsonify({'error': 'Title required'}), 400
    if lat == 0 and lng == 0:
        return jsonify({'error': 'Could not determine coordinates. Please provide lat/lng manually or a more specific location.'}), 400
    pin = {
        'id':          f'pin_{int(datetime.now().timestamp())}',
        'title':       data.get('title', '').strip(),
        'category':    data.get('category', 'phenomena'),
        'location':    data.get('location', '').strip(),
        'lat':         lat,
        'lng':         lng,
        'date':        data.get('date', datetime.now(timezone.utc).strftime('%Y-%m-%d')),
        'witnesses':   int(data.get('witnesses', 1)),
        'desc':        data.get('desc', '').strip(),
        'verified':    bool(data.get('verified', True)),
        'source':      data.get('source', 'manual'),
        'case_number': data.get('case_number', ''),
        'created_at':  datetime.now(timezone.utc).isoformat(),
    }
    pins = get_pins()
    pins.insert(0, pin)
    save_json(PINS_FILE, pins)
    audit_log('pin_created', {'id': pin['id'], 'location': pin['location']})
    return jsonify({'status': 'created', 'pin': pin})

@app.route('/admin/map/pins/<pin_id>', methods=['PATCH'])
def admin_update_pin(pin_id):
    err = require_admin()
    if err: return err
    data = request.get_json(silent=True) or {}
    pins = get_pins()
    for i, p in enumerate(pins):
        if p['id'] == pin_id:
            pins[i].update(data)
            save_json(PINS_FILE, pins)
            return jsonify({'status': 'updated', 'pin': pins[i]})
    return jsonify({'error': 'Not found'}), 404

@app.route('/admin/map/pins/<pin_id>', methods=['DELETE'])
def admin_delete_pin(pin_id):
    err = require_admin()
    if err: return err
    pins = [p for p in get_pins() if p['id'] != pin_id]
    save_json(PINS_FILE, pins)
    audit_log('pin_deleted', {'id': pin_id})
    return jsonify({'status': 'deleted'})

@app.route('/admin/map/pins/<pin_id>/verify', methods=['POST'])
def admin_verify_pin(pin_id):
    err = require_admin()
    if err: return err
    pins = get_pins()
    for i, p in enumerate(pins):
        if p['id'] == pin_id:
            pins[i]['verified'] = True
            save_json(PINS_FILE, pins)
            audit_log('pin_verified', {'id': pin_id})
            return jsonify({'status': 'verified'})
    return jsonify({'error': 'Not found'}), 404

@app.route('/admin/geocode', methods=['POST'])
def admin_geocode():
    err = require_admin()
    if err: return err
    data     = request.get_json(silent=True) or {}
    location = data.get('location', '').strip()
    if not location:
        return jsonify({'error': 'Location required'}), 400
    lat, lng = geocode_location(location)
    if lat == 0 and lng == 0:
        return jsonify({'error': 'Location not found'}), 404
    return jsonify({'lat': lat, 'lng': lng})

@app.route('/admin/members', methods=['GET'])
def admin_get_members():
    err = require_admin()
    if err: return err
    return jsonify({'members': get_members(), 'total': len(get_members())})

@app.route('/admin/members/<member_id>', methods=['PATCH'])
def admin_update_member(member_id):
    err = require_admin()
    if err: return err
    data    = request.get_json(silent=True) or {}
    members = get_members()
    for i, m in enumerate(members):
        if m['id'] == member_id:
            members[i].update(data)
            save_json(MEMBERS_FILE, members)
            audit_log('member_updated', {'id': member_id, 'changes': list(data.keys())})
            return jsonify({'status': 'updated'})
    return jsonify({'error': 'Not found'}), 404

@app.route('/admin/email/test', methods=['POST'])
def admin_test_email():
    err = require_admin()
    if err: return err
    config = get_config()
    team   = config.get('admin_team', [])
    recipients = [m.get('email', '').strip() for m in team
                  if m.get('active', True) and m.get('email', '').strip()]
    if not recipients:
        agent = os.getenv('AGENT_EMAIL', '')
        if agent:
            recipients = [agent]
        else:
            return jsonify({'error': 'No recipients configured. Add team members or set AGENT_EMAIL in .env'}), 400
    smtp_host = os.getenv('SMTP_HOST', '')
    smtp_user = os.getenv('SMTP_USER', '')
    smtp_pass = os.getenv('SMTP_PASS', '')
    if not all([smtp_host, smtp_user, smtp_pass]):
        return jsonify({'error': 'SMTP not configured in .env (SMTP_HOST, SMTP_USER, SMTP_PASS)'}), 400
    body = '<div style="background:#07070f;color:#e8e0ff;font-family:Georgia;padding:2rem"><h3 style="color:#c084fc">Strangeness IS — Test Email</h3><p>SMTP is working correctly.</p></div>'
    sent_to = []
    for r in recipients:
        if send_email(r, 'Strangeness IS — SMTP Test', body):
            sent_to.append(r)
    if not sent_to:
        return jsonify({'error': 'Failed to send to any recipients. Check SMTP credentials.'}), 500
    audit_log('test_email_sent', {'recipients': sent_to})
    return jsonify({'status': 'sent', 'to': sent_to, 'count': len(sent_to)})


@app.route('/admin/email/digest', methods=['POST'])
def admin_send_digest():
    """Send the latest live report to all active members with report alerts enabled."""
    err = require_admin()
    if err: return err
    reports = get_reports()
    live    = [r for r in reports if r.get('status') == 'live']
    if not live:
        return jsonify({'error': 'No published reports to send'}), 400
    report  = live[0]
    members = get_members()
    recipients = [m.get('email','').strip() for m in members
                  if m.get('active') and m.get('email') and m.get('alerts_reports', True)]
    if not recipients:
        return jsonify({'error': 'No active members with report alerts enabled'}), 400
    subject = f'Strangeness IS — {report.get("headline", "New Report")}'
    html    = (
        f'<div style="background:#07070f;color:#e8e0ff;font-family:Georgia,serif;'
        f'max-width:600px;margin:0 auto;padding:2rem">'
        f'<h2 style="color:#c084fc">{report.get("headline","New Report")}</h2>'
        f'<p style="color:#a78bfa">Strangeness Index: {report.get("strangeness_index",7.5)}/10</p>'
        f'<p>{report.get("summary","")}</p>'
        f'<a href="{SITE_URL}/report.html" style="background:#7c3aed;color:#fff;'
        f'padding:.75rem 1.5rem;border-radius:5px;text-decoration:none;display:inline-block;margin-top:1rem">'
        f'Read Full Report</a></div>'
    )
    def _send_all():
        for email in recipients:
            send_email(email, subject, html)
    threading.Thread(target=_send_all, daemon=True).start()
    audit_log('digest_sent', {'report_id': report.get('id'), 'recipients': len(recipients)})
    return jsonify({'status': 'sending', 'report': report.get('headline',''), 'recipients': len(recipients)})

@app.route('/admin/audit-log', methods=['GET'])
def admin_get_audit_log():
    err = require_admin()
    if err: return err
    log   = load_json(AUDIT_LOG_FILE, [])
    limit = request.args.get('limit', 100, type=int)
    return jsonify({'log': log[:limit], 'total': len(log)})

@app.route('/admin/headlines', methods=['GET'])
def admin_get_headlines():
    err = require_admin()
    if err: return err
    db = load_json(HEADLINES_FILE, [])
    db.sort(key=lambda h: h.get('fetched_at', ''), reverse=True)
    # Extract unique sources from stored records
    all_sources = sorted(set(h.get('source', '') for h in db if h.get('source')))
    # Apply source filter if provided
    source_filter = request.args.get('source', '').strip()
    if source_filter:
        db = [h for h in db if h.get('source', '') == source_filter]
    # Apply limit (default 200, max 500)
    limit = min(500, int(request.args.get('limit', 200)))
    total_unfiltered = len(load_json(HEADLINES_FILE, []))
    return jsonify({
        'headlines': db[:limit],
        'total':     total_unfiltered,
        'filtered':  len(db),
        'sources':   all_sources,
    })

@app.route('/admin/headlines/fetch', methods=['POST'])
def admin_fetch_headlines():
    err = require_admin()
    if err: return err
    def _run():
        try:
            count = scan_all_news_sources()
            app.logger.info(f'Manual headline scan complete: {count} new headlines')
        except Exception as e:
            app.logger.error(f'Manual headline scan failed: {e}')
    threading.Thread(target=_run, daemon=True).start()
    return jsonify({
        'status':  'scanning',
        'message': 'Scan started. Refresh the headline list in 30-60 seconds to see results.',
    })

@app.route('/admin/headlines/<headline_id>', methods=['DELETE'])
def admin_delete_headline(headline_id):
    err = require_admin()
    if err: return err
    db = load_json(HEADLINES_FILE, [])
    before = len(db)
    db = [h for h in db if h.get('id') != headline_id]
    if len(db) == before:
        return jsonify({'error': 'Not found'}), 404
    save_json(HEADLINES_FILE, db)
    return jsonify({'status': 'deleted', 'remaining': len(db)})

@app.route('/admin/headlines/clear', methods=['POST'])
def admin_clear_headlines():
    err = require_admin()
    if err: return err
    save_json(HEADLINES_FILE, [])
    audit_log('headlines_cleared', {})
    return jsonify({'status': 'cleared'})

@app.route('/admin/team/invite', methods=['POST'])
def admin_invite_team():
    err = require_admin()
    if err: return err
    data    = request.get_json(silent=True) or {}
    member  = data.get('member', {})
    email   = member.get('email', '').strip().lower()
    name    = member.get('name', '')
    role    = member.get('role', 'admin')
    if not email or not re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', email):
        return jsonify({'error': 'Valid email required'}), 400
    temp_pw = secrets.token_urlsafe(12)
    config  = get_config()
    team    = config.get('admin_team', [])
    found   = False
    for m in team:
        if m.get('email', '').lower() == email:
            m['password_hash'] = hashlib.sha256(temp_pw.encode()).hexdigest()
            m['password_set']  = False
            found = True
            break
    if not found:
        team.insert(0, {
            'email':         email,
            'name':          name,
            'role':          role,
            'active':        True,
            'alerts':        member.get('alerts', []),
            'password_hash': hashlib.sha256(temp_pw.encode()).hexdigest(),
            'password_set':  False,
        })
    config['admin_team'] = team
    save_json(CONFIG_FILE, config)
    html = (f'<div style="background:#07070f;color:#e8e0ff;font-family:Georgia;padding:2rem">'
            f'<h2 style="color:#c084fc">Strangeness IS — Admin Access</h2>'
            f'<p>Hi {name}, you have been added as <strong>{role}</strong>.</p>'
            f'<p>Admin URL: <a href="{SITE_URL}/admin.html" style="color:#c084fc">{SITE_URL}/admin.html</a></p>'
            f'<p>Temporary password: <strong style="font-family:monospace;color:#d4a843">{temp_pw}</strong></p>'
            f'<p style="color:#4a4060;font-size:.8rem">Change your password after first login.</p></div>')
    sent = send_email(email, 'Strangeness IS — Your admin access details', html)
    audit_log('team_member_invited', {'email': email, 'role': role})
    return jsonify({'status': 'invited', 'email': email, 'sent': sent})

@app.route('/admin/team/login', methods=['POST'])
def admin_team_login():
    data     = request.get_json(silent=True) or {}
    email    = data.get('email', '').strip().lower()
    password = data.get('password', '').strip()
    if not email or not password:
        return jsonify({'error': 'Email and password required'}), 400
    # Master admin key check (no email required for master key)
    if password == ADMIN_KEY:
        return jsonify({'status': 'ok', 'role': 'superadmin', 'name': 'Admin', 'password_set': True, 'admin_key': ADMIN_KEY})
    config = get_config()
    team   = config.get('admin_team', [])
    member = next((m for m in team if m.get('email', '').lower() == email), None)
    if not member:
        return jsonify({'error': 'No admin account found'}), 404
    pw_hash = hashlib.sha256(password.encode()).hexdigest()
    if pw_hash != member.get('password_hash', ''):
        return jsonify({'error': 'Incorrect password'}), 401
    return jsonify({'status': 'ok', 'role': member.get('role', 'admin'),
                    'name': member.get('name', ''), 'password_set': member.get('password_set', True),
                    'admin_key': ADMIN_KEY})

@app.route('/admin/team/set-password', methods=['POST'])
def admin_team_set_password():
    """Set permanent password for a team member on first login."""
    data     = request.get_json(silent=True) or {}
    email    = data.get('email', '').strip().lower()
    temp_pw  = data.get('temp_password', '').strip()
    new_pw   = data.get('new_password', '').strip()
    if not email or not temp_pw or not new_pw:
        return jsonify({'error': 'email, temp_password and new_password required'}), 400
    if len(new_pw) < 8:
        return jsonify({'error': 'Password must be at least 8 characters'}), 400
    config = get_config()
    team   = config.get('admin_team', [])
    member = next((m for m in team if m.get('email', '').lower() == email), None)
    if not member:
        return jsonify({'error': 'No admin account found'}), 404
    temp_hash = hashlib.sha256(temp_pw.encode()).hexdigest()
    if temp_hash != member.get('password_hash', ''):
        return jsonify({'error': 'Temporary password incorrect'}), 401
    member['password_hash'] = hashlib.sha256(new_pw.encode()).hexdigest()
    member['password_set']  = True
    config['admin_team'] = team
    save_json(CONFIG_FILE, config)
    audit_log('team_password_set', {'email': email})
    return jsonify({'status': 'password_set', 'role': member.get('role', 'admin'),
                    'name': member.get('name', '')})

@app.route('/analytics/event', methods=['POST'])
def track_frontend_event():
    data  = request.get_json(silent=True) or {}
    event = data.get('event', '')
    props = data.get('properties', {})
    if event:
        analytics = get_analytics()
        analytics['events'].append({'event': event, 'props': props, 'ts': datetime.now(timezone.utc).isoformat()})
        analytics['events'] = analytics['events'][-500:]
        save_json(ANALYTICS_FILE, analytics)
    return jsonify({'tracked': True})

@app.route('/admin/analytics', methods=['GET'])
def admin_get_analytics():
    err = require_admin()
    if err: return err
    analytics = get_analytics()
    members   = get_members()
    reports   = get_reports()
    return jsonify({
        'page_views':     analytics.get('page_views', {}),
        'total_members':  len(members),
        'active_members': len([m for m in members if m.get('active')]),
        'total_reports':  len(reports),
        'live_reports':   len([r for r in reports if r.get('status') == 'live']),
        'oracle_intel':   len(load_json(ORACLE_INTEL_FILE, [])),
        'recent_events':  analytics.get('events', [])[-20:],
    })

# ═══════════════════════════════════════════════════════════
# PIPELINE STATUS — verify scanner + generator are working
# ═══════════════════════════════════════════════════════════


@app.route('/admin/comments', methods=['GET'])
def admin_get_comments():
    """Return oracle conversation excerpts for the comments moderation panel."""
    err = require_admin()
    if err: return err
    intel = load_json(ORACLE_INTEL_FILE, [])
    limit = request.args.get('limit', 100, type=int)
    comments = []
    for record in intel[:limit]:
        comments.append({
            'id':           record.get('id', ''),
            'timestamp':    record.get('timestamp', ''),
            'session_id':   record.get('session_id', ''),
            'category':     record.get('phenomenon_category', ''),
            'summary':      record.get('key_details', ''),
            'emotional_tone': record.get('emotional_tone', ''),
            'locations':    record.get('locations', []),
        })
    return jsonify({'comments': comments, 'total': len(comments)})

@app.route('/admin/comments/<comment_id>', methods=['DELETE'])
def admin_delete_comment(comment_id):
    """Remove an oracle intel record by ID (used for moderation)."""
    err = require_admin()
    if err: return err
    intel = load_json(ORACLE_INTEL_FILE, [])
    before = len(intel)
    intel  = [r for r in intel if r.get('id') != comment_id]
    if len(intel) == before:
        return jsonify({'error': 'Not found'}), 404
    save_json(ORACLE_INTEL_FILE, intel)
    audit_log('comment_deleted', {'id': comment_id})
    return jsonify({'status': 'deleted'})


@app.route('/admin/signal-intel', methods=['GET'])
def admin_get_signal_intel():
    """Signal Intelligence panel — mainstream headlines scored for hidden patterns."""
    err = require_admin()
    if err: return err
    db       = load_json(SIGNAL_INTEL_FILE, [])
    min_score = request.args.get('min_score', 4, type=int)
    source    = request.args.get('source', '')
    reviewed  = request.args.get('reviewed', '')
    filtered  = [r for r in db if r.get('score', 0) >= min_score]
    if source:
        filtered = [r for r in filtered if r.get('source') == source]
    if reviewed == 'false':
        filtered = [r for r in filtered if not r.get('reviewed')]
    elif reviewed == 'true':
        filtered = [r for r in filtered if r.get('reviewed')]
    return jsonify({
        'total':   len(db),
        'signals': filtered[:100],
        'sources': sorted(set(r.get('source','') for r in db)),
    })

@app.route('/admin/signal-intel/<signal_id>', methods=['PATCH', 'DELETE'])
def admin_update_signal(signal_id):
    """Update notes/reviewed status or delete a signal."""
    err = require_admin()
    if err: return err
    db = load_json(SIGNAL_INTEL_FILE, [])
    for i, r in enumerate(db):
        if r.get('id') == signal_id:
            if request.method == 'DELETE':
                db.pop(i)
                save_json(SIGNAL_INTEL_FILE, db)
                return jsonify({'status': 'deleted'})
            data = request.get_json(silent=True) or {}
            if 'notes'    in data: db[i]['notes']    = data['notes'][:500]
            if 'reviewed' in data: db[i]['reviewed'] = bool(data['reviewed'])
            save_json(SIGNAL_INTEL_FILE, db)
            return jsonify({'status': 'updated', 'signal': db[i]})
    return jsonify({'error': 'Not found'}), 404

@app.route('/admin/signal-intel/analyze', methods=['POST'])
def admin_analyze_signals():
    """Use GPT to find cross-signal patterns across recent high-score headlines."""
    err = require_admin()
    if err: return err
    if not os.getenv('OPENAI_API_KEY'):
        return jsonify({'error': 'OpenAI not configured'}), 400
    db      = load_json(SIGNAL_INTEL_FILE, [])
    top     = [r for r in db if r.get('score', 0) >= 6][:20]
    if len(top) < 3:
        return jsonify({'error': 'Need at least 3 high-score signals to analyze'}), 400
    lines   = [f"[{r['source']}] {r['title']} (score:{r['score']}, keywords:{','.join(r['keywords'])})"
               for r in top]
    prompt  = (
        "You are a pattern analyst for a paranormal intelligence network. "
        "Study these mainstream news headlines that have been flagged as potentially significant. "
        "Find hidden connections, recurring themes, and what they might collectively suggest. "
        "Be specific. Reference actual headlines. Speak as an investigator, not a journalist.\n\n"
        + "\n".join(lines)
    )
    try:
        response = client.chat.completions.create(
            model='gpt-4o-mini',
            messages=[{'role': 'user', 'content': prompt}],
            max_tokens=600, temperature=0.7,
        )
        analysis = response.choices[0].message.content.strip()
        return jsonify({'analysis': analysis, 'signals_analyzed': len(top)})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/admin/pipeline/status', methods=['GET'])
def admin_pipeline_status():
    err = require_admin()
    if err: return err
    db          = load_json(HEADLINES_FILE, [])
    reports     = get_reports()
    oracle_intel = load_json(ORACLE_INTEL_FILE, [])
    latest_hl   = db[0] if db else None
    latest_rep  = reports[0] if reports else None
    config      = get_config()
    sources     = get_all_news_sources()
    return jsonify({
        'status':               'running',
        'total_sources':        len(sources),
        'headlines_stored':     len(db),
        'latest_headline':      latest_hl.get('title','—') if latest_hl else '—',
        'latest_headline_time': latest_hl.get('fetched_at','—') if latest_hl else '—',
        'oracle_intel_records': len(oracle_intel),
        'total_reports':        len(reports),
        'latest_report':        latest_rep.get('headline','—') if latest_rep else '—',
        'latest_report_time':   latest_rep.get('created_at','—') if latest_rep else '—',
        'report_schedule':      config.get('report_time','07:00'),
        'scan_interval':        '15 minutes',
    })

# ═══════════════════════════════════════════════════════════
# MASTER CATEGORIES
# ═══════════════════════════════════════════════════════════

@app.route('/admin/categories', methods=['GET'])
def admin_get_categories():
    err = require_admin()
    if err: return err
    config = get_config()
    cats = config.get('master_categories') or MASTER_CATEGORIES
    return jsonify({'categories': cats})

@app.route('/admin/categories', methods=['POST'])
def admin_save_categories():
    err = require_admin()
    if err: return err
    data = request.get_json(silent=True) or {}
    cats = data.get('categories', '').strip()
    if not cats:
        return jsonify({'error': 'Categories cannot be empty'}), 400
    config = get_config()
    config['master_categories'] = cats
    save_json(CONFIG_FILE, config)
    audit_log('categories_saved')
    return jsonify({'status': 'saved'})

# ═══════════════════════════════════════════════════════════
# NEWS SCANNER — runs every 15 minutes, stores to headlines DB
# Sources configurable via admin. Feeds the Writer.
# ═══════════════════════════════════════════════════════════

NEWS_SOURCES = [
    # ── PRIMARY CASE DATABASES — structured incident data ────
    ('https://nuforc.org/rss/recent-reports.xml',                             'NUFORC'),
    ('https://www.phantomsandmonsters.com/feeds/posts/default',               'Phantoms & Monsters'),
    ('https://singularfortean.com/feed/',                                     'Singular Fortean'),
    ('https://www.ufocasebook.com/feed/',                                     'UFO Casebook'),
    ('https://www.nicap.org/rss.xml',                                         'NICAP'),
    ('https://www.openminds.tv/feed/',                                        'Open Minds TV'),
    ('https://thedebrief.org/feed/',                                          'The Debrief'),
    ('https://www.theblackvault.com/casebook/feed/',                          'The Black Vault'),
    ('https://mysteriousuniverse.org/feed/',                                  'Mysterious Universe'),
    ('https://anomalyinfo.com/feed',                                          'Anomaly Info'),
    ('https://www.theparacast.com/feed/',                                     'The Paracast'),
    ('https://www.coasttocoastam.com/feed/recent/',                           'Coast to Coast AM'),
    ('https://www.unknowncountry.com/feed/',                                  'Unknown Country'),
    ('https://www.cryptomundo.com/feed/',                                     'Cryptomundo'),
    ('https://www.bfro.net/news/rss.asp',                                     'BFRO'),
    ('https://www.lochnessinvestigation.com/feed/',                           'Loch Ness Investigation'),
    # ── REDDIT CASE COMMUNITIES ───────────────────────────────
    ('https://www.reddit.com/r/UFOs/.rss',                                    'Reddit UFOs'),
    ('https://www.reddit.com/r/Paranormal/.rss',                              'Reddit Paranormal'),
    ('https://www.reddit.com/r/conspiracy/.rss',                              'Reddit Conspiracy'),
    ('https://www.reddit.com/r/aliens/.rss',                                  'Reddit Aliens'),
    ('https://www.reddit.com/r/cryptids/.rss',                                'Reddit Cryptids'),
    ('https://www.reddit.com/r/bigfoot/.rss',                                 'Reddit Bigfoot'),
    ('https://www.reddit.com/r/Missing411/.rss',                              'Reddit Missing411'),
    ('https://www.reddit.com/r/SkinwalkerRanch/.rss',                        'Reddit Skinwalker'),
    ('https://www.reddit.com/r/HighStrangeness/.rss',                        'Reddit HighStrangeness'),
    ('https://www.reddit.com/r/NDE/.rss',                                    'Reddit NDE'),
    ('https://www.reddit.com/r/RemoteViewing/.rss',                          'Reddit RemoteViewing'),
    ('https://www.reddit.com/r/ufo/.rss',                                    'Reddit UFO'),
    # ── Google News targeted searches ─────────────────────────
    ('https://news.google.com/rss/search?q=UAP+UFO+disclosure&hl=en-US',              'Google UAP'),
    ('https://news.google.com/rss/search?q=paranormal+cryptid&hl=en-US',             'Google Paranormal'),
    ('https://news.google.com/rss/search?q=government+disclosure+alien&hl=en-US',    'Google Disclosure'),
    ('https://news.google.com/rss/search?q=bigfoot+sasquatch&hl=en-US',              'Google Bigfoot'),
    ('https://news.google.com/rss/search?q=haunted+ghost+sighting&hl=en-US',         'Google Ghosts'),
    ('https://news.google.com/rss/search?q=NHI+non+human+intelligence&hl=en-US',     'Google NHI'),
    ('https://news.google.com/rss/search?q=whistleblower+classified+pentagon&hl=en-US','Google Whistleblower'),
    ('https://news.google.com/rss/search?q=strange+phenomenon+unexplained&hl=en-US', 'Google Strange'),
    ('https://news.google.com/rss/search?q=dogman+mothman+cryptid&hl=en-US',         'Google Cryptids'),
    ('https://news.google.com/rss/search?q=ancient+mystery+archaeology&hl=en-US',    'Google Ancient'),
    # ── Major news outlets (RSS feeds) ────────────────────────
    ('https://feeds.abcnews.com/abcnews/topstories',            'ABC News'),
    ('http://rss.cnn.com/rss/edition.rss',                     'CNN'),
    ('https://feeds.nbcnews.com/nbcnews/public/news',           'NBC News'),
    ('https://www.cbsnews.com/latest/rss/main',                 'CBS News'),
    ('https://www.foxnews.com/feeds/latest.rss',               'Fox News'),
    ('https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml', 'New York Times'),
    ('https://feeds.washingtonpost.com/rss/homepage',           'Washington Post'),
    ('https://feeds.bbci.co.uk/news/rss.xml',                  'BBC News'),
    ('https://www.dailymail.co.uk/news/index.rss',             'Daily Mail'),
    ('https://www.theguardian.com/us/rss',                     'The Guardian'),
    ('https://www.npr.org/rss/rss.php?id=1001',                'NPR'),
    ('https://www.usatoday.com/rss/news/',                     'USA Today'),
    ('https://time.com/feed()/',                                 'Time'),
    ('https://slate.com/feeds/all.rss',                        'Slate'),
    ('https://www.vox.com/rss/index.xml',                      'Vox'),
    ('https://www.thedailybeast.com/rss',                      'Daily Beast'),
    ('https://www.salon.com/feed',                             'Salon'),
    ('https://www.theatlantic.com/feed/all/',                  'The Atlantic'),
    ('https://techcrunch.com/feed/',                           'TechCrunch'),
    ('https://feeds.businessinsider.com/custom/all',            'Business Insider'),
    ('https://thehill.com/feed',                               'The Hill'),
    ('https://www.politico.com/rss/politicopicks.xml',         'Politico'),
    ('https://www.axios.com/feeds/feed.rss',                   'Axios'),
    ('https://www.newsmax.com/rss/NewsMax-News/16/',            'Newsmax'),
    ('https://www.washingtontimes.com/rss/headlines/',          'Washington Times'),
    ('https://www.breitbart.com/feed/',                        'Breitbart'),
    ('https://www.zerohedge.com/fullrss2.xml',                 'Zero Hedge'),
    ('https://www.independent.co.uk/rss',                      'The Independent'),
    ('https://www.telegraph.co.uk/rss.xml',                    'The Telegraph'),
    ('https://www.mirror.co.uk/news/rss.xml',                  'Mirror Online'),
    ('https://www.express.co.uk/news.rss',                     'Daily Express'),
    ('https://www.usnews.com/rss/news',                        'US News'),
    ('https://reason.com/feed/',                               'Reason'),
    ('https://www.nationalreview.com/feed/',                   'National Review'),
    ('https://www.marketwatch.com/rss/topstories',             'MarketWatch'),
    ('https://www.forbes.com/news/feed2/',                     'Forbes'),
    ('https://engadget.com/rss.xml',                           'Engadget'),
    ('https://www.chicagotribune.com/arcio/rss/',              'Chicago Tribune'),
    ('https://www.latimes.com/rss2.0.xml',                    'LA Times'),
    ('https://www.boston.com/rss/news/',                       'Boston Globe'),
    ('https://www.sfgate.com/news/feed/San-Francisco-News-484203.php', 'SFGate'),
    ('https://www.nydailynews.com/news/?rss=y',                'NY Daily News'),
]

def get_all_news_sources():
    """Return built-in sources merged with any custom sources from admin config."""
    config  = get_config()
    custom  = config.get('custom_news_sources', [])  # list of {url, name} dicts
    sources = list(NEWS_SOURCES)
    for src in custom:
        if src.get('url') and src.get('name'):
            sources.append((src['url'], src['name']))
    return sources


# ── Call Log Database ─────────────────────────────────────────────────────────

@app.route('/admin/calls', methods=['GET'])
def admin_get_calls():
    err = require_admin()
    if err: return err
    calls = load_json(CALL_LOG_FILE, [])
    calls.sort(key=lambda c: c.get('created_at',''), reverse=True)
    return jsonify({'calls': calls, 'total': len(calls)})

@app.route('/admin/calls', methods=['POST'])
def admin_log_call():
    err = require_admin()
    if err: return err
    data = request.get_json(silent=True) or {}
    year_str   = datetime.now().strftime('%Y')
    existing   = load_json(CALL_LOG_FILE, [])
    year_calls = [c for c in existing if c.get('case_number','').startswith(f'SI-CALL-{year_str}-')]
    call = {
        'id':             f'call_{int(datetime.now(timezone.utc).timestamp())}',
        'case_number':    data.get('case_number') or f"SI-CALL-{year_str}-{len(year_calls)+1:04d}",
        'created_at':     datetime.now(timezone.utc).isoformat(),
        'caller_name':    data.get('caller_name','').strip(),
        'phone':          data.get('phone','').strip(),
        'email':          data.get('email','').strip(),
        'member_id':      data.get('member_id','').strip(),
        'plan':           data.get('plan','').strip(),
        'duration_min':   int(data.get('duration_min', 0)),
        'call_type':      data.get('call_type','sighting_report'),
        'category':       data.get('category','').strip(),
        'location':       data.get('location','').strip(),
        'summary':        data.get('summary','').strip(),
        'transcript':     data.get('transcript','').strip(),
        'follow_up':      data.get('follow_up', False),
        'follow_up_note': data.get('follow_up_note','').strip(),
        'status':         data.get('status','completed'),
        'agent':          data.get('agent','').strip(),
    }
    calls = load_json(CALL_LOG_FILE, [])
    calls.insert(0, call)
    save_json(CALL_LOG_FILE, calls)
    if call['email']:
        members = get_members()
        for m in members:
            if m.get('email','').lower() == call['email'].lower():
                if 'calls' not in m: m['calls'] = []
                m['calls'].append(call['id'])
                m['last_call'] = call['created_at']
                break
        save_json(MEMBERS_FILE, members)
    return jsonify({'status': 'logged', 'call': call})

@app.route('/admin/calls/<call_id>', methods=['PATCH'])
def admin_update_call(call_id):
    err = require_admin()
    if err: return err
    data  = request.get_json(silent=True) or {}
    calls = load_json(CALL_LOG_FILE, [])
    for c in calls:
        if c.get('id') == call_id:
            for k, v in data.items(): c[k] = v
            save_json(CALL_LOG_FILE, calls)
            return jsonify({'status': 'updated', 'call': c})
    return jsonify({'error': 'Not found'}), 404

@app.route('/admin/calls/<call_id>', methods=['DELETE'])
def admin_delete_call(call_id):
    err = require_admin()
    if err: return err
    calls = [c for c in load_json(CALL_LOG_FILE, []) if c.get('id') != call_id]
    save_json(CALL_LOG_FILE, calls)
    return jsonify({'status': 'deleted'})

@app.route('/admin/news-sources', methods=['GET'])
def admin_get_news_sources():
    err = require_admin()
    if err: return err
    config  = get_config()
    custom  = config.get('custom_news_sources', [])
    builtin = [{'url': url, 'name': name, 'builtin': True} for url, name in NEWS_SOURCES]
    return jsonify({'builtin': builtin, 'custom': custom, 'total': len(builtin) + len(custom)})

@app.route('/admin/news-sources', methods=['POST'])
def admin_add_news_source():
    err = require_admin()
    if err: return err
    data = request.get_json(silent=True) or {}
    url  = data.get('url', '').strip()
    name = data.get('name', '').strip()
    if not url or not name:
        return jsonify({'error': 'url and name required'}), 400
    config  = get_config()
    custom  = config.get('custom_news_sources', [])
    # Deduplicate
    if any(s.get('url') == url for s in custom):
        return jsonify({'error': 'Source already exists'}), 400
    custom.append({'url': url, 'name': name})
    config['custom_news_sources'] = custom
    save_json(CONFIG_FILE, config)
    audit_log('news_source_added', {'name': name, 'url': url})
    return jsonify({'status': 'added', 'total': len(custom)})

@app.route('/admin/news-sources/<int:idx>', methods=['DELETE'])
def admin_delete_news_source(idx):
    err = require_admin()
    if err: return err
    config = get_config()
    custom = config.get('custom_news_sources', [])
    if idx < 0 or idx >= len(custom):
        return jsonify({'error': 'Invalid index'}), 404
    removed = custom.pop(idx)
    config['custom_news_sources'] = custom
    save_json(CONFIG_FILE, config)
    audit_log('news_source_removed', {'name': removed.get('name')})
    return jsonify({'status': 'removed'})

@app.route('/admin/news-sources/scan', methods=['POST'])
def admin_scan_news_now():
    err = require_admin()
    if err: return err
    def _run():
        try:
            count = scan_all_news_sources()
            app.logger.info(f'Admin news scan complete: {count} new headlines')
        except Exception as e:
            app.logger.error(f'Admin news scan failed: {e}')
    threading.Thread(target=_run, daemon=True).start()
    return jsonify({
        'status':  'scanning',
        'sources': len(get_all_news_sources()),
        'message': 'Scan started. Refresh in 30-60 seconds to see results.',
    })

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)