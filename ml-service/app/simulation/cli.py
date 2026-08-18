import argparse
import os
from dotenv import load_dotenv
from app.simulation.core import generate_and_load_data
from app.simulation.engine import run_simulation

def main():
    parser = argparse.ArgumentParser(description="SCARLET Phase 3 Digital Twin CLI")
    parser.add_argument("--generate", action="store_true", help="Generate synthetic data")
    parser.add_argument("--run-sim", action="store_true", help="Run simulation")
    parser.add_argument("--days", type=int, default=7, help="Simulation days")
    
    args = parser.parse_args()
    load_dotenv()
    
    db_kwargs = {
        "host": os.getenv("DB_HOST", "localhost"),
        "port": os.getenv("DB_PORT", "5432"),
        "dbname": os.getenv("DB_NAME", "scarlet"),
        "user": os.getenv("DB_USER", "scarlet_user"),
        "password": os.getenv("DB_PASSWORD", "your_db_password_here"),
    }
    
    if args.generate:
        print("Generating data...")
        generate_and_load_data(db_kwargs)
        
    if args.run_sim:
        print(f"Running simulation for {args.days} days...")
        try:
            metrics = run_simulation(db_kwargs, days=args.days)
            print("Simulation Complete!")
            print(f"Metrics: {metrics}")
        except Exception as e:
            print(f"Simulation failed (likely DB connection issue): {e}")

if __name__ == "__main__":
    main()
