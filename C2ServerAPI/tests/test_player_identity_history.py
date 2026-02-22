import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from core.database_models import Base, PlayerRecord, Sanction
import core.database_manager as dbm


class PlayerIdentityHistoryTests(unittest.TestCase):
    def setUp(self):
        # In-memory SQLite that persists across sessions
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)

        self._orig_get_session = dbm.get_session
        dbm.get_session = lambda: self.Session()

    def tearDown(self):
        dbm.get_session = self._orig_get_session
        self.engine.dispose()

    def test_update_last_seen_creates_record_and_history_entry(self):
        rec = dbm.PlayerManager.update_last_seen("P1", "Alice")
        self.assertIsNotNone(rec)

        session = self.Session()
        try:
            db_rec = session.query(PlayerRecord).filter_by(playfab_id="P1").first()
            self.assertEqual(db_rec.username, "Alice")
            self.assertIsNotNone(db_rec.last_seen)
            self.assertEqual(db_rec.get_name_history(), [])

            entries = session.query(Sanction).filter_by(playfab_id="P1").all()
            self.assertEqual(len(entries), 1)
            self.assertEqual(entries[0].sanction_type, "last_seen_update")
        finally:
            session.close()

    def test_username_change_appends_name_history_and_creates_username_update_entry(self):
        dbm.PlayerManager.update_last_seen("P2", "Alice")
        dbm.PlayerManager.update_last_seen("P2", "Bob")

        session = self.Session()
        try:
            db_rec = session.query(PlayerRecord).filter_by(playfab_id="P2").first()
            self.assertEqual(db_rec.username, "Bob")
            self.assertIn("Alice", db_rec.get_name_history())

            entries = (
                session.query(Sanction)
                .filter_by(playfab_id="P2")
                .order_by(Sanction.id.asc())
                .all()
            )
            # 1st call: last_seen_update
            # 2nd call: username_update + last_seen_update
            self.assertEqual(len(entries), 3)
            self.assertTrue(any(e.sanction_type == "username_update" for e in entries))
            u = next(e for e in entries if e.sanction_type == "username_update")
            self.assertEqual(u.previous_username, "Alice")
            self.assertEqual(u.username, "Bob")
        finally:
            session.close()

    def test_note_set_and_clear(self):
        rec = dbm.PlayerManager.set_note("P3", "hello")
        self.assertIsNotNone(rec)
        self.assertEqual(rec.note, "hello")

        ok = dbm.PlayerManager.clear_note("P3")
        self.assertTrue(ok)

        session = self.Session()
        try:
            db_rec = session.query(PlayerRecord).filter_by(playfab_id="P3").first()
            self.assertIsNone(db_rec.note)
        finally:
            session.close()

    def test_create_sanction_upserts_player_and_tracks_name_history(self):
        dbm.SanctionManager.create_sanction(
            sanction_type="ban",
            playfab_id="P4",
            username="Alice",
            reason="test",
            duration_hours=1,
        )
        dbm.SanctionManager.create_sanction(
            sanction_type="kick",
            playfab_id="P4",
            username="Bob",
            reason="test2",
        )

        session = self.Session()
        try:
            db_rec = session.query(PlayerRecord).filter_by(playfab_id="P4").first()
            self.assertEqual(db_rec.username, "Bob")
            self.assertIn("Alice", db_rec.get_name_history())

            entries = session.query(Sanction).filter_by(playfab_id="P4").all()
            # 2 sanctions + 1 username_update
            self.assertEqual(len(entries), 3)
            self.assertTrue(any(e.sanction_type == "username_update" for e in entries))
        finally:
            session.close()


if __name__ == "__main__":
    unittest.main()
