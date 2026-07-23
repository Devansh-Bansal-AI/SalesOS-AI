# ============================================================
# SalesOS AI — Seed Data Script
#
# Populates the database with realistic demo data:
#   - 1 Organization
#   - 3 Users (admin, sales_manager, sales_rep)
#   - 15 Leads across all pipeline stages
#   - Lead scores, activities, meetings
#
# Usage:
#   python -m scripts.seed_data
# ============================================================

import asyncio
import sys
from datetime import UTC, datetime, timedelta
from uuid import uuid4

# Ensure the app module is importable
sys.path.insert(0, ".")


async def seed():
    """Seed the database with demo data."""
    from app.core.security import hash_password
    from app.db.session import async_session_factory, engine
    from app.models.activity import Activity
    from app.models.lead import Lead, LeadScore
    from app.models.meeting import Meeting
    from app.models.organization import Organization
    from app.models.user import User

    print("[SEED] SalesOS AI — Seeding demo data...")

    async with async_session_factory() as session:
        # ── Organization ────────────────────────────────────
        org = Organization(
            id=uuid4(),
            name="Acme Corp (Demo)",
            slug="acme-corp-demo",
            domain="acme-demo.com",
            plan="enterprise",
        )
        session.add(org)
        await session.flush()
        print(f"  [OK] Organization: {org.name} ({org.id})")

        # ── Users ───────────────────────────────────────────
        password_hash = hash_password("Demo1234!")

        admin = User(
            id=uuid4(),
            organization_id=org.id,
            email="admin@acme-demo.com",
            password_hash=password_hash,
            first_name="Sarah",
            last_name="Chen",
            role="admin",
        )
        manager = User(
            id=uuid4(),
            organization_id=org.id,
            email="manager@acme-demo.com",
            password_hash=password_hash,
            first_name="Marcus",
            last_name="Johnson",
            role="sales_manager",
        )
        rep = User(
            id=uuid4(),
            organization_id=org.id,
            email="rep@acme-demo.com",
            password_hash=password_hash,
            first_name="Emily",
            last_name="Rodriguez",
            role="sales_rep",
        )
        session.add_all([admin, manager, rep])
        await session.flush()
        print(f"  [OK] Users: {admin.email}, {manager.email}, {rep.email}")
        print(f"     Password for all: Demo1234!")

        # ── Leads ───────────────────────────────────────────
        now = datetime.now(UTC)

        leads_data = [
            # Hot leads
            {"email": "cto@stripe.com", "first_name": "Alex", "last_name": "Rivera",
             "job_title": "CTO", "status": "qualified", "priority": "critical",
             "source": "website", "assigned_to": rep.id},
            {"email": "vp.sales@shopify.com", "first_name": "Jordan", "last_name": "Kim",
             "job_title": "VP Sales", "status": "meeting_booked", "priority": "high",
             "source": "referral", "assigned_to": rep.id},
            {"email": "head.ops@notion.com", "first_name": "Taylor", "last_name": "Nguyen",
             "job_title": "Head of Operations", "status": "demo", "priority": "high",
             "source": "linkedin", "assigned_to": manager.id},
            # Warm leads
            {"email": "director@figma.com", "first_name": "Casey", "last_name": "Park",
             "job_title": "Director of Sales", "status": "contacted", "priority": "medium",
             "source": "website", "assigned_to": rep.id},
            {"email": "manager@linear.app", "first_name": "Morgan", "last_name": "Davis",
             "job_title": "Sales Manager", "status": "outreach", "priority": "medium",
             "source": "cold_email", "assigned_to": rep.id},
            {"email": "lead@vercel.com", "first_name": "Riley", "last_name": "Thompson",
             "job_title": "Team Lead", "status": "nurture", "priority": "medium",
             "source": "webinar", "assigned_to": manager.id},
            # New leads
            {"email": "founder@startup.io", "first_name": "Sam", "last_name": "Lee",
             "job_title": "CEO", "status": "new", "priority": "high",
             "source": "website", "assigned_to": None},
            {"email": "cro@enterprise.co", "first_name": "Jamie", "last_name": "Wilson",
             "job_title": "CRO", "status": "new", "priority": "critical",
             "source": "referral", "assigned_to": None},
            {"email": "vp@growth.ai", "first_name": "Drew", "last_name": "Martinez",
             "job_title": "VP Growth", "status": "new", "priority": "medium",
             "source": "linkedin", "assigned_to": None},
            # Converted
            {"email": "ceo@closedwon.com", "first_name": "Pat", "last_name": "Anderson",
             "job_title": "CEO", "status": "converted", "priority": "critical",
             "source": "referral", "assigned_to": rep.id},
            {"email": "svp@bigdeal.com", "first_name": "Chris", "last_name": "Taylor",
             "job_title": "SVP Sales", "status": "converted", "priority": "high",
             "source": "website", "assigned_to": manager.id},
            # Negotiation
            {"email": "head@negotiate.io", "first_name": "Quinn", "last_name": "Brown",
             "job_title": "Head of Revenue", "status": "negotiation", "priority": "high",
             "source": "website", "assigned_to": rep.id},
            # Disqualified / Lost
            {"email": "intern@tiny.co", "first_name": "Blake", "last_name": "Smith",
             "job_title": "Intern", "status": "disqualified", "priority": "none",
             "source": "website", "assigned_to": None},
            {"email": "info@competitor.com", "first_name": "Avery", "last_name": "Clark",
             "job_title": "BDR", "status": "lost", "priority": "low",
             "source": "cold_email", "assigned_to": rep.id},
            {"email": "test@spam.net", "first_name": "Test", "last_name": "User",
             "job_title": None, "status": "disqualified", "priority": "none",
             "source": "website", "assigned_to": None},
        ]

        lead_objects = []
        for i, ld in enumerate(leads_data):
            lead = Lead(
                id=uuid4(),
                organization_id=org.id,
                email=ld["email"],
                first_name=ld["first_name"],
                last_name=ld["last_name"],
                job_title=ld.get("job_title"),
                status=ld["status"],
                priority=ld.get("priority"),
                source=ld["source"],
                assigned_to=ld.get("assigned_to"),
                created_at=now - timedelta(days=25 - i),
            )
            lead_objects.append(lead)
            session.add(lead)

        await session.flush()
        print(f"  [OK] Leads: {len(lead_objects)} created across all stages")

        # ── Lead Scores ─────────────────────────────────────
        scores = [
            (lead_objects[0], 92, "critical", "demo_request", "immediate", 0.95),
            (lead_objects[1], 85, "high", "pricing", "this_week", 0.88),
            (lead_objects[2], 78, "high", "evaluation", "this_month", 0.82),
            (lead_objects[3], 65, "medium", "general", "this_quarter", 0.75),
            (lead_objects[4], 58, "medium", "pricing", "this_month", 0.70),
            (lead_objects[6], 72, "high", "demo_request", "this_week", 0.80),
            (lead_objects[7], 88, "critical", "pricing", "immediate", 0.92),
            (lead_objects[9], 95, "critical", "demo_request", "immediate", 0.98),
            (lead_objects[10], 82, "high", "evaluation", "this_week", 0.85),
            (lead_objects[11], 76, "high", "pricing", "this_month", 0.78),
            (lead_objects[12], 12, "none", "general", "unknown", 0.90),
        ]

        for lead, score, priority, intent, urgency, confidence in scores:
            ls = LeadScore(
                id=uuid4(),
                lead_id=lead.id,
                organization_id=org.id,
                score=score,
                priority=priority,
                intent=intent,
                urgency=urgency,
                confidence=confidence,
                created_at=lead.created_at + timedelta(minutes=5),
            )
            session.add(ls)

        await session.flush()
        print(f"  [OK] Lead Scores: {len(scores)} qualification scores")

        # ── Activities ──────────────────────────────────────
        activity_templates = [
            ("lead_created", "[NEW] Lead created", True),
            ("qualification_completed", "[AI] Qualification completed", True),
            ("enrichment_completed", "[INFO] Company enrichment completed", True),
            ("outreach_sent", "[EMAIL] Outreach email sent", True),
            ("meeting_booked", "[CALENDAR] Meeting booked", True),
        ]

        activity_count = 0
        for lead in lead_objects[:8]:  # Add activities to first 8 leads
            for j, (atype, title, is_ai) in enumerate(activity_templates[:3]):
                activity = Activity(
                    id=uuid4(),
                    organization_id=org.id,
                    lead_id=lead.id,
                    activity_type=atype,
                    title=title,
                    description=f"Automated activity for {lead.first_name} {lead.last_name}",
                    is_ai_generated=is_ai,
                    created_at=lead.created_at + timedelta(hours=j),
                )
                session.add(activity)
                activity_count += 1

        await session.flush()
        print(f"  [OK] Activities: {activity_count} timeline entries")

        # ── Meetings ────────────────────────────────────────
        meetings_data = [
            (lead_objects[1], rep, "Discovery Call — Shopify", "discovery", "confirmed"),
            (lead_objects[2], manager, "Product Demo — Notion", "demo", "pending"),
            (lead_objects[9], rep, "Final Review — ClosedWon", "follow_up", "completed"),
        ]

        for lead, host, title, mtype, mstatus in meetings_data:
            meeting = Meeting(
                id=uuid4(),
                organization_id=org.id,
                lead_id=lead.id,
                host_user_id=host.id,
                title=title,
                meeting_type=mtype,
                status=mstatus,
                scheduled_at=now + timedelta(days=2),
                duration_minutes=30,
                timezone="UTC",
            )
            session.add(meeting)

        await session.flush()
        print(f"  [OK] Meetings: {len(meetings_data)} booked")

        # Commit
        await session.commit()

    print("\n[SUCCESS] Seed data complete!")
    print(f"\n  Login credentials:")
    print(f"    Admin:   admin@acme-demo.com   / Demo1234!")
    print(f"    Manager: manager@acme-demo.com / Demo1234!")
    print(f"    Rep:     rep@acme-demo.com     / Demo1234!")


if __name__ == "__main__":
    asyncio.run(seed())
