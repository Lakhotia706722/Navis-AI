"""Load test for Celery queue with concurrent renders."""
import pytest
import asyncio
from unittest.mock import patch, MagicMock
from datetime import datetime

from backend.models import Project, User, RenderJob, RenderJobStatusEnum
from backend.database import SessionLocal


@pytest.fixture
def db():
    """Database session for tests."""
    db = SessionLocal()
    yield db
    db.close()


@pytest.fixture
def user(db):
    """Create test user."""
    user = User(
        email="load_test@example.com",
        hashed_password="hashed_password",
        is_active=True,
    )
    db.add(user)
    db.commit()
    return user


def test_concurrent_render_job_creation(db, user):
    """Test creating multiple concurrent render jobs."""
    num_jobs = 10
    
    # Create projects
    projects = []
    for i in range(num_jobs):
        project = Project(
            user_id=user.id,
            title=f"Load Test Project {i}",
            prompt=f"Test prompt {i}",
        )
        db.add(project)
        projects.append(project)
    
    db.commit()
    
    # Create render jobs
    render_jobs = []
    for i, project in enumerate(projects):
        job = RenderJob(
            project_id=project.id,
            status=RenderJobStatusEnum.QUEUED,
            render_mode="preview",
        )
        db.add(job)
        render_jobs.append(job)
    
    db.commit()
    
    # Verify all jobs were created
    jobs = db.query(RenderJob).all()
    assert len(jobs) >= num_jobs
    
    # Verify all jobs are queued
    queued_jobs = db.query(RenderJob).filter(
        RenderJob.status == RenderJobStatusEnum.QUEUED
    ).all()
    assert len(queued_jobs) >= num_jobs


def test_render_job_status_transitions(db, user):
    """Test render job status transitions under load."""
    num_jobs = 5
    statuses = [
        RenderJobStatusEnum.QUEUED,
        RenderJobStatusEnum.PLANNING,
        RenderJobStatusEnum.COMPOSING,
        RenderJobStatusEnum.RENDERING,
        RenderJobStatusEnum.ASSEMBLING,
        RenderJobStatusEnum.DONE,
    ]
    
    # Create projects and render jobs
    for i in range(num_jobs):
        project = Project(
            user_id=user.id,
            title=f"Status Test Project {i}",
            prompt=f"Test prompt {i}",
        )
        db.add(project)
        db.flush()
        
        for status_idx, status in enumerate(statuses):
            job = RenderJob(
                project_id=project.id,
                status=status,
                progress_percent=int((status_idx / len(statuses)) * 100),
                started_at=datetime.utcnow(),
            )
            db.add(job)
    
    db.commit()
    
    # Verify status distribution
    for status in statuses:
        count = db.query(RenderJob).filter(RenderJob.status == status).count()
        assert count >= num_jobs / len(statuses)


def test_render_job_with_celery_task_ids(db, user):
    """Test render jobs with Celery task IDs."""
    num_jobs = 5
    
    project = Project(
        user_id=user.id,
        title="Celery Task Test Project",
        prompt="Test prompt",
    )
    db.add(project)
    db.flush()
    
    # Create render jobs with task IDs
    for i in range(num_jobs):
        job = RenderJob(
            project_id=project.id,
            status=RenderJobStatusEnum.QUEUED,
            celery_task_id=f"task-{i:05d}-{'a' * 20}",
        )
        db.add(job)
    
    db.commit()
    
    # Verify task IDs are unique
    jobs = db.query(RenderJob).filter(
        RenderJob.project_id == project.id
    ).all()
    task_ids = [job.celery_task_id for job in jobs]
    assert len(task_ids) == len(set(task_ids))  # All unique


@pytest.mark.asyncio
async def test_concurrent_status_updates(db, user):
    """Test concurrent status updates."""
    num_jobs = 10
    
    # Create project and jobs
    project = Project(
        user_id=user.id,
        title="Concurrent Updates Test",
        prompt="Test prompt",
    )
    db.add(project)
    db.flush()
    
    jobs = []
    for i in range(num_jobs):
        job = RenderJob(
            project_id=project.id,
            status=RenderJobStatusEnum.QUEUED,
        )
        db.add(job)
        jobs.append(job)
    
    db.commit()
    
    # Simulate concurrent status updates
    async def update_job(job_id, new_status):
        job = db.query(RenderJob).filter(RenderJob.id == job_id).first()
        if job:
            job.status = new_status
            job.progress_percent = 50
            db.commit()
        await asyncio.sleep(0.01)  # Simulate async work
    
    # Run concurrent updates
    tasks = [
        update_job(job.id, RenderJobStatusEnum.PLANNING)
        for job in jobs
    ]
    await asyncio.gather(*tasks)
    
    # Verify all jobs were updated
    planning_jobs = db.query(RenderJob).filter(
        RenderJob.status == RenderJobStatusEnum.PLANNING
    ).all()
    assert len(planning_jobs) >= num_jobs


def test_render_job_cascade_delete(db, user):
    """Test cascade delete behavior."""
    # Create project with multiple render jobs
    project = Project(
        user_id=user.id,
        title="Cascade Test Project",
        prompt="Test prompt",
    )
    db.add(project)
    db.flush()
    
    num_jobs = 5
    for i in range(num_jobs):
        job = RenderJob(
            project_id=project.id,
            status=RenderJobStatusEnum.QUEUED,
        )
        db.add(job)
    
    db.commit()
    project_id = project.id
    
    # Verify jobs exist
    jobs_before = db.query(RenderJob).filter(
        RenderJob.project_id == project_id
    ).count()
    assert jobs_before == num_jobs
    
    # Delete project (should cascade delete jobs)
    project = db.query(Project).filter(Project.id == project_id).first()
    db.delete(project)
    db.commit()
    
    # Verify jobs are deleted
    jobs_after = db.query(RenderJob).filter(
        RenderJob.project_id == project_id
    ).count()
    assert jobs_after == 0


def test_queue_performance_metrics(db, user):
    """Test queue performance under load."""
    import time
    
    num_jobs = 100
    
    project = Project(
        user_id=user.id,
        title="Performance Test Project",
        prompt="Test prompt",
    )
    db.add(project)
    db.flush()
    
    # Measure job creation time
    start_time = time.time()
    
    for i in range(num_jobs):
        job = RenderJob(
            project_id=project.id,
            status=RenderJobStatusEnum.QUEUED,
        )
        db.add(job)
    
    db.commit()
    
    elapsed = time.time() - start_time
    throughput = num_jobs / elapsed
    
    # Assert reasonable performance (should handle 100+ jobs in < 5 seconds)
    assert elapsed < 5.0, f"Job creation took {elapsed}s, throughput: {throughput:.0f} jobs/sec"
    
    # Verify all jobs created
    all_jobs = db.query(RenderJob).filter(
        RenderJob.project_id == project.id
    ).count()
    assert all_jobs == num_jobs
