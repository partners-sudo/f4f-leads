"""
Main script to run competitor discovery.

Usage:
    python run_competitor_discovery.py
"""

import asyncio
import sys
from discovery.competitor_discovery import CompetitorDiscovery
from utils.logger import logger


async def main():
    """Main function to run competitor discovery."""
    
    # Competitor brands to search for
    brands = ["Funko", "Tubbz", "Cable guys"]
    
    # You can also pass brands as command line arguments
    if len(sys.argv) > 1:
        brands = sys.argv[1:]
    
    logger.info(f"Starting competitor discovery for: {', '.join(brands)}")
    
    # Initialize discovery
    discovery = CompetitorDiscovery(brands)
    
    # Run all discovery strategies
    discovery_stats = await discovery.discover_all()
    
    # Save to Supabase
    save_stats = await discovery.save_to_supabase()
    
    # Generate and print report
    report = discovery.generate_report(discovery_stats, save_stats)
    print("\n" + report)
    
    # Also save report to file
    report_file = "competitor_discovery_report.txt"
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)
    logger.info(f"\n📄 Report saved to: {report_file}")
    
    return discovery_stats, save_stats


if __name__ == '__main__':
    asyncio.run(main())

