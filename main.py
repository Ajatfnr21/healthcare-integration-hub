#!/usr/bin/env python3
"""
Healthcare Integration Hub - HL7/FHIR data integration platform
"""

import json
import asyncio
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum
import click

class MessageType(Enum):
    HL7 = "hl7"
    FHIR = "fhir"
    DICOM = "dicom"

@dataclass
class PatientRecord:
    id: str
    name: str
    dob: str
    medical_record_number: str
    diagnoses: List[str]
    medications: List[Dict]
    last_updated: str

class HL7Parser:
    """Parse HL7 v2.x messages"""
    
    def parse(self, message: str) -> Dict:
        segments = message.split('\r')
        result = {"segments": {}}
        
        for segment in segments:
            if not segment:
                continue
            fields = segment.split('|')
            segment_type = fields[0]
            result["segments"][segment_type] = fields
            
        # Extract patient info from PID
        if 'PID' in result["segments"]:
            pid = result["segments"]['PID']
            result["patient"] = {
                "id": pid[3] if len(pid) > 3 else "",
                "name": pid[5] if len(pid) > 5 else "",
                "dob": pid[7] if len(pid) > 7 else ""
            }
            
        return result
    
    def generate(self, patient: PatientRecord) -> str:
        """Generate HL7 ADT^A08 message"""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        
        msh = f"MSH|^~\&|INTEGRATION_HUB|HOSPITAL|RECEIVER|FACILITY|{timestamp}||ADT^A08|{patient.id}|P|2.5"
        pid = f"PID|1||{patient.medical_record_number}||{patient.name}||{patient.dob}||"
        
        return f"{msh}\r{pid}\r"

class FHIRClient:
    """FHIR R4 client for resource operations"""
    
    def __init__(self, base_url: str = "http://localhost:8080/fhir"):
        self.base_url = base_url
        
    def create_patient(self, patient: PatientRecord) -> Dict:
        """Create Patient resource"""
        fhir_patient = {
            "resourceType": "Patient",
            "id": patient.id,
            "identifier": [{
                "system": "http://hospital.org/mrn",
                "value": patient.medical_record_number
            }],
            "name": [{"text": patient.name}],
            "birthDate": patient.dob
        }
        return fhir_patient
    
    def to_patient_record(self, fhir_resource: Dict) -> PatientRecord:
        """Convert FHIR Patient to internal format"""
        name = fhir_resource.get("name", [{}])[0].get("text", "")
        identifiers = fhir_resource.get("identifier", [])
        mrn = next((i.get("value", "") for i in identifiers 
                   if i.get("system", "").endswith("mrn")), "")
        
        return PatientRecord(
            id=fhir_resource.get("id", ""),
            name=name,
            dob=fhir_resource.get("birthDate", ""),
            medical_record_number=mrn,
            diagnoses=[],
            medications=[],
            last_updated=datetime.now().isoformat()
        )

class HealthcareIntegrationHub:
    def __init__(self):
        self.hl7_parser = HL7Parser()
        self.fhir_client = FHIRClient()
        self.records: Dict[str, PatientRecord] = {}
        
    def process_hl7(self, message: str) -> PatientRecord:
        """Process HL7 message and store record"""
        parsed = self.hl7_parser.parse(message)
        
        patient_data = parsed.get("patient", {})
        record = PatientRecord(
            id=patient_data.get("id", ""),
            name=patient_data.get("name", ""),
            dob=patient_data.get("dob", ""),
            medical_record_number=patient_data.get("id", ""),
            diagnoses=[],
            medications=[],
            last_updated=datetime.now().isoformat()
        )
        
        self.records[record.id] = record
        return record
    
    def convert_to_fhir(self, patient_id: str) -> Optional[Dict]:
        """Convert internal record to FHIR"""
        record = self.records.get(patient_id)
        if not record:
            return None
        return self.fhir_client.create_patient(record)
    
    def list_patients(self) -> List[PatientRecord]:
        return list(self.records.values())

@click.group()
def cli():
    """Healthcare Integration Hub CLI"""
    pass

@cli.command()
@click.argument('message_file')
def parse_hl7(message_file):
    """Parse HL7 message from file"""
    hub = HealthcareIntegrationHub()
    
    with open(message_file, 'r') as f:
        message = f.read()
    
    record = hub.process_hl7(message)
    print(f"\n✅ Parsed HL7 message")
    print(f"   Patient: {record.name}")
    print(f"   MRN: {record.medical_record_number}")

@cli.command()
@click.argument('patient_id')
def to_fhir(patient_id):
    """Convert patient to FHIR format"""
    hub = HealthcareIntegrationHub()
    
    # Add sample patient
    hub.records[patient_id] = PatientRecord(
        id=patient_id,
        name="John Doe",
        dob="1980-01-15",
        medical_record_number="MRN123456",
        diagnoses=[],
        medications=[],
        last_updated=datetime.now().isoformat()
    )
    
    fhir_resource = hub.convert_to_fhir(patient_id)
    if fhir_resource:
        print(json.dumps(fhir_resource, indent=2))

if __name__ == "__main__":
    cli()
