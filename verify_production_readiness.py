'''
Production readiness verification script for InstaBids.

This script performs a comprehensive verification of the InstaBids
system to ensure it is ready for production deployment.
'''
import os
import sys
import logging
import asyncio
import importlib
import inspect
import subprocess
from pathlib import Path

logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

logger = logging.getLogger(__name__)

# Check if all required environment variables are set or have fallbacks
REQUIRED_ENV_VARS = [
    "SUPABASE_URL",
    "SUPABASE_KEY",
    "SUPABASE_ANON_KEY",
    "SUPABASE_SERVICE_ROLE",
    "GOOGLE_API_KEY",
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY"
]

# Required modules for testing
REQUIRED_MODULES = [
    "src.instabids.a2a_comm",
    "src.instabids.agents.base_agent",
    "src.instabids.agents.contractor_agent",
    "src.instabids.tools.bid_visualization_tool",
    "memory.persistent_memory",
    "src.instabids.adk"
]

# Required files for GitHub Actions
REQUIRED_GITHUB_FILES = [
    ".github/workflows/ci.yml"
]

async def check_env_vars():
    """Check if all required environment variables are set."""
    logger.info("Checking environment variables...")
    
    missing_vars = []
    for var in REQUIRED_ENV_VARS:
        if var not in os.environ:
            missing_vars.append(var)
    
    if missing_vars:
        logger.warning("Missing environment variables: %s", missing_vars)
        logger.warning("For CI/CD, these must be set as GitHub secrets")
    else:
        logger.info("All required environment variables are set")
    
    return len(missing_vars) == 0

async def check_imports():
    """Check if all required modules can be imported."""
    logger.info("Checking module imports...")
    
    missing_modules = []
    for module_name in REQUIRED_MODULES:
        try:
            module = importlib.import_module(module_name)
            logger.info("Successfully imported %s", module_name)
        except ImportError as e:
            logger.error("Failed to import %s: %s", module_name, str(e))
            missing_modules.append(module_name)
    
    if missing_modules:
        logger.warning("Missing modules: %s", missing_modules)
    else:
        logger.info("All required modules are available")
    
    return len(missing_modules) == 0

async def check_github_files():
    """Check if all required GitHub files exist."""
    logger.info("Checking GitHub files...")
    
    missing_files = []
    for file_path in REQUIRED_GITHUB_FILES:
        full_path = Path(file_path)
        if not full_path.exists():
            logger.error("Missing GitHub file: %s", file_path)
            missing_files.append(file_path)
        else:
            logger.info("Found GitHub file: %s", file_path)
    
    if missing_files:
        logger.warning("Missing GitHub files: %s", missing_files)
    else:
        logger.info("All required GitHub files are available")
    
    return len(missing_files) == 0

async def run_units_tests():
    """Run unit tests to verify functionality."""
    logger.info("Running unit tests...")
    
    try:
        result = subprocess.run(
            ["python", "-m", "pytest", "tests/unit", "-v"], 
            capture_output=True, 
            text=True
        )
        
        if result.returncode == 0:
            logger.info("Unit tests passed")
            logger.debug(result.stdout)
            return True
        else:
            logger.error("Unit tests failed")
            logger.error(result.stderr)
            return False
    except Exception as e:
        logger.error("Error running unit tests: %s", str(e))
        return False

async def verify_ci_workflow():
    """Verify the CI workflow configuration."""
    logger.info("Verifying CI workflow...")
    
    ci_path = Path(".github/workflows/ci.yml")
    if not ci_path.exists():
        logger.error("CI workflow file not found")
        return False
    
    try:
        with open(ci_path, 'r') as f:
            content = f.read()
        
        # Check for essential components
        checks = {
            "Python setup": "actions/setup-python" in content,
            "Environment variables": "SUPABASE_URL" in content and "GOOGLE_API_KEY" in content,
            "Unit tests": "pytest" in content,
            "Deployment": "deploy" in content
        }
        
        for check, passed in checks.items():
            if passed:
                logger.info("CI workflow check passed: %s", check)
            else:
                logger.error("CI workflow check failed: %s", check)
        
        all_passed = all(checks.values())
        if all_passed:
            logger.info("CI workflow verification passed")
        else:
            logger.error("CI workflow verification failed")
        
        return all_passed
    except Exception as e:
        logger.error("Error verifying CI workflow: %s", str(e))
        return False

async def check_database_migrations():
    """Check if database migrations are available."""
    logger.info("Checking database migrations...")
    
    migrations_dir = Path("supabase/migrations")
    if not migrations_dir.exists():
        logger.error("Migrations directory not found")
        return False
    
    migrations = list(migrations_dir.glob("*.sql"))
    if not migrations:
        logger.warning("No migrations found in %s", migrations_dir)
        return False
    
    logger.info("Found %d migrations", len(migrations))
    return True

async def generate_final_report(results):
    """Generate a final verification report."""
    logger.info("Generating final verification report...")
    
    report = {
        "environment_variables": results.get("env_vars", False),
        "module_imports": results.get("imports", False),
        "github_files": results.get("github_files", False),
        "unit_tests": results.get("unit_tests", False),
        "ci_workflow": results.get("ci_workflow", False),
        "database_migrations": results.get("database_migrations", False)
    }
    
    # Calculate overall readiness
    all_checks_passed = all(report.values())
    
    # Generate report
    report_path = Path("PRODUCTION_READINESS_REPORT.md")
    with open(report_path, 'w') as f:
        f.write("# InstaBids Production Readiness Report\n\n")
        f.write(f"Generated: {asyncio.current_task().get_loop().time()}\n\n")
        
        f.write("## Overall Readiness\n\n")
        if all_checks_passed:
            f.write("✅ **READY FOR PRODUCTION DEPLOYMENT**\n\n")
        else:
            f.write("❌ **NOT READY FOR PRODUCTION DEPLOYMENT**\n\n")
            f.write("Some checks failed. Please see details below.\n\n")
        
        f.write("## Check Results\n\n")
        for check, passed in report.items():
            status = "✅ Passed" if passed else "❌ Failed"
            f.write(f"- {check.replace('_', ' ').title()}: {status}\n")
        
        f.write("\n## Deployment Instructions\n\n")
        f.write("1. Ensure all GitHub secrets are set for the CI/CD pipeline\n")
        f.write("2. Merge the `fix/testing-infrastructure` branch to `main`\n")
        f.write("3. Verify that the CI workflow runs successfully\n")
        f.write("4. Deploy the package to production\n")
    
    logger.info("Final report generated: %s", report_path)
    return all_checks_passed

async def main():
    """Main verification function."""
    logger.info("Starting production readiness verification...")
    
    # Add the current directory to the path
    sys.path.insert(0, os.path.abspath("."))
    
    # Run all verification checks
    results = {
        "env_vars": await check_env_vars(),
        "imports": await check_imports(),
        "github_files": await check_github_files(),
        "unit_tests": await run_units_tests(),
        "ci_workflow": await verify_ci_workflow(),
        "database_migrations": await check_database_migrations()
    }
    
    # Generate final report
    all_passed = await generate_final_report(results)
    
    # Print overall result
    if all_passed:
        logger.info("All verification checks passed")
        logger.info("The system is ready for production deployment")
    else:
        logger.error("Some verification checks failed")
        logger.error("The system is NOT ready for production deployment")
    
    return all_passed

if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(0 if result else 1)