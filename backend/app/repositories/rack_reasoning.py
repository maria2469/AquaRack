"""
Repository for rack reasoning results persistence.
Handles saving and retrieving rack reasoning results for fleet dashboard.
"""
from datetime import datetime
from typing import List, Optional
from sqlalchemy.orm import Session
from app.models_ext import RackReasoningResult
from app.database import SessionLocal
import logging

logger = logging.getLogger("aquamind.rack_reasoning_repo")


class RackReasoningRepository:
    """Repository for rack reasoning results operations."""
    
    @staticmethod
    def save_rack_result(
        db: Session,
        rack_id: str,
        device_id: str,
        is_laptop: bool,
        success: bool,
        recommendation: Optional[str] = None,
        rationale: Optional[str] = None,
        expected_water_saving: Optional[float] = None,
        confidence: Optional[float] = None,
        reasoning_time_ms: Optional[float] = None,
        run_id: Optional[str] = None,
        api_response: Optional[dict] = None,
        reasoning_logs: Optional[List[dict]] = None,
        cpu_factor: Optional[float] = None,
        gpu_factor: Optional[float] = None,
        ram_factor: Optional[float] = None,
        cooling_efficiency: Optional[float] = None,
        hardware_age: Optional[float] = None
    ) -> RackReasoningResult:
        """Save or update a rack reasoning result."""
        try:
            # Check if result already exists for this rack
            existing_result = db.query(RackReasoningResult).filter(
                RackReasoningResult.rack_id == rack_id
            ).first()
            
            if existing_result:
                # Update existing result
                existing_result.success = success
                existing_result.recommendation = recommendation
                existing_result.rationale = rationale
                existing_result.expected_water_saving = expected_water_saving
                existing_result.confidence = confidence
                existing_result.reasoning_time_ms = reasoning_time_ms
                existing_result.run_id = run_id
                existing_result.api_response = api_response
                existing_result.reasoning_logs = reasoning_logs
                existing_result.updated_at = datetime.utcnow()
                
                # Update profile factors if provided
                if cpu_factor is not None:
                    existing_result.cpu_factor = cpu_factor
                if gpu_factor is not None:
                    existing_result.gpu_factor = gpu_factor
                if ram_factor is not None:
                    existing_result.ram_factor = ram_factor
                if cooling_efficiency is not None:
                    existing_result.cooling_efficiency = cooling_efficiency
                if hardware_age is not None:
                    existing_result.hardware_age = hardware_age
                
                db.commit()
                db.refresh(existing_result)
                logger.info(f"Updated rack reasoning result for {rack_id}")
                return existing_result
            else:
                # Create new result
                new_result = RackReasoningResult(
                    rack_id=rack_id,
                    device_id=device_id,
                    is_laptop=is_laptop,
                    success=success,
                    recommendation=recommendation,
                    rationale=rationale,
                    expected_water_saving=expected_water_saving,
                    confidence=confidence,
                    reasoning_time_ms=reasoning_time_ms,
                    run_id=run_id,
                    api_response=api_response,
                    reasoning_logs=reasoning_logs,
                    cpu_factor=cpu_factor,
                    gpu_factor=gpu_factor,
                    ram_factor=ram_factor,
                    cooling_efficiency=cooling_efficiency,
                    hardware_age=hardware_age
                )
                db.add(new_result)
                db.commit()
                db.refresh(new_result)
                logger.info(f"Created new rack reasoning result for {rack_id}")
                return new_result
        except Exception as e:
            db.rollback()
            logger.error(f"Error saving rack reasoning result for {rack_id}: {e}")
            raise
    
    @staticmethod
    def get_rack_result(db: Session, rack_id: str) -> Optional[RackReasoningResult]:
        """Get a rack reasoning result by rack ID."""
        try:
            return db.query(RackReasoningResult).filter(
                RackReasoningResult.rack_id == rack_id
            ).first()
        except Exception as e:
            logger.error(f"Error getting rack reasoning result for {rack_id}: {e}")
            return None
    
    @staticmethod
    def get_all_rack_results(db: Session) -> List[RackReasoningResult]:
        """Get all rack reasoning results."""
        try:
            return db.query(RackReasoningResult).order_by(
                RackReasoningResult.created_at.desc()
            ).all()
        except Exception as e:
            logger.error(f"Error getting all rack reasoning results: {e}")
            return []
    
    @staticmethod
    def get_successful_racks(db: Session) -> List[RackReasoningResult]:
        """Get all successful rack reasoning results."""
        try:
            return db.query(RackReasoningResult).filter(
                RackReasoningResult.success == True
            ).order_by(RackReasoningResult.created_at.desc()).all()
        except Exception as e:
            logger.error(f"Error getting successful rack results: {e}")
            return []
    
    @staticmethod
    def get_fleet_summary(db: Session) -> dict:
        """Get fleet summary statistics."""
        try:
            all_results = db.query(RackReasoningResult).all()
            successful_results = [r for r in all_results if r.success]
            
            total_savings = sum(r.expected_water_saving or 0 for r in successful_results)
            avg_confidence = (
                sum(r.confidence or 0 for r in successful_results) / len(successful_results)
                if successful_results else 0
            )
            
            if successful_results:
                confidences = [r.confidence or 0 for r in successful_results]
                min_conf = min(confidences) * 100
                max_conf = max(confidences) * 100
                conf_range = f"{min_conf:.0f}-{max_conf:.0f}%"
            else:
                conf_range = "0-0%"
            
            avg_time = (
                sum(r.reasoning_time_ms or 0 for r in successful_results) / len(successful_results) / 1000
                if successful_results else 0
            )
            
            return {
                "total_racks": len(all_results),
                "successful_racks": len(successful_results),
                "failed_racks": len(all_results) - len(successful_results),
                "total_water_savings": total_savings,
                "avg_confidence": avg_confidence,
                "confidence_range": conf_range,
                "avg_time_seconds": avg_time
            }
        except Exception as e:
            logger.error(f"Error getting fleet summary: {e}")
            return {
                "total_racks": 0,
                "successful_racks": 0,
                "failed_racks": 0,
                "total_water_savings": 0,
                "avg_confidence": 0,
                "confidence_range": "0-0%",
                "avg_time_seconds": 0
            }
    
    @staticmethod
    def delete_rack_result(db: Session, rack_id: str) -> bool:
        """Delete a rack reasoning result."""
        try:
            result = db.query(RackReasoningResult).filter(
                RackReasoningResult.rack_id == rack_id
            ).first()
            if result:
                db.delete(result)
                db.commit()
                logger.info(f"Deleted rack reasoning result for {rack_id}")
                return True
            return False
        except Exception as e:
            db.rollback()
            logger.error(f"Error deleting rack reasoning result for {rack_id}: {e}")
            return False
    
    @staticmethod
    def clear_all_results(db: Session) -> bool:
        """Clear all rack reasoning results."""
        try:
            db.query(RackReasoningResult).delete()
            db.commit()
            logger.info("Cleared all rack reasoning results")
            return True
        except Exception as e:
            db.rollback()
            logger.error(f"Error clearing all rack reasoning results: {e}")
            return False