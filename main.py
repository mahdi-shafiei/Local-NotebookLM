from pathlib import Path
import argparse
import logging

from steps.step1 import step1
from steps.step2 import step2
from steps.step3 import step3
from steps.step4 import step4
from steps.helpers import set_provider

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    parser = argparse.ArgumentParser(description="Generate a podcast from a PDF document")
    
    # Required arguments
    parser.add_argument("--pdf", type=str, required=True, help="Path to the PDF file")
    
    # Optional arguments
    parser.add_argument("--config", type=str, help="Path to a custom config file")
    parser.add_argument("--format", type=str, choices=["podcast", "interview", "panel-discussion", "debate", "summary", "narration", "storytelling", "explainer", "lecture", "tutorial", "q-and-a", "news-report", "executive-brief", "meeting-minutes", "analysis"], default="summary", help="Output format type")
    parser.add_argument("--length", type=str, choices=["short", "medium", "long", "very-long"], default="medium", help="Content length")
    parser.add_argument("--style", type=str, choices=["normal", "friendly", "professional", "academic", "casual", "technical", "gen-z", "funny"], default="normal", help="Content style")
    parser.add_argument("--preference", type=str, help="Additional preferences or instructions")
    parser.add_argument("--output-dir", type=str, default="./output", help="Directory to store output files")
    parser.add_argument("--skip-to", type=int, choices=[1, 2, 3, 4], help="Skip to a specific step (1-4)")
    
    args = parser.parse_args()
    
    # Load config
    if args.config:
        import json
        with open(args.config, 'r') as f:
            config = json.load(f)
    else:
        from config import base_config
        config = base_config
    
    # Create output directories
    output_base = Path(args.output_dir)
    output_dirs = {
        "step1": output_base / "step1",
        "step2": output_base / "step2",
        "step3": output_base / "step3"
    }
    
    for dir_path in output_dirs.values():
        dir_path.mkdir(parents=True, exist_ok=True)
    
    # Set up clients
    small_text_client = set_provider(config=config["Small-Text-Model"]["provider"])
    big_text_client = set_provider(config=config["Big-Text-Model"]["provider"])
    tts_client = set_provider(config=config["Text-To-Speech-Model"]["provider"])
    
    try:
        # Initialize variables for file paths that might be skipped
        cleaned_text_file = None
        transcript_file = None
        
        # Step 1: Process PDF
        if not args.skip_to or args.skip_to <= 1:
            logger.info("Step 1: Processing PDF...")
            cleaned_text_file = step1(
                client=small_text_client,
                pdf_path=args.pdf,
                config=config,
                output_dir=str(output_dirs["step1"])
            )
        else:
            # If skipping, find the most recent output file from step1
            logger.info("Skipping Step 1, looking for existing output...")
            step1_files = list(output_dirs["step1"].glob("*.txt"))
            if step1_files:
                cleaned_text_file = str(sorted(step1_files, key=lambda x: x.stat().st_mtime, reverse=True)[0])
                logger.info(f"Using existing file from Step 1: {cleaned_text_file}")
            else:
                logger.error("No output files found from Step 1. Cannot skip this step.")
                return 1
        
        # Step 2: Generate transcript
        if not args.skip_to or args.skip_to <= 2:
            logger.info("Step 2: Generating transcript...")
            _, transcript_file = step2(
                client=big_text_client,
                config=config,
                input_file=cleaned_text_file,
                output_dir=str(output_dirs["step2"]),
                format_type=args.format,
                length=args.length,
                style=args.style
            )
        else:
            # If skipping, find the most recent output file from step2
            logger.info("Skipping Step 2, looking for existing output...")
            step2_files = list(output_dirs["step2"].glob("*.txt"))
            if step2_files:
                transcript_file = str(sorted(step2_files, key=lambda x: x.stat().st_mtime, reverse=True)[0])
                logger.info(f"Using existing file from Step 2: {transcript_file}")
            else:
                logger.error("No output files found from Step 2. Cannot skip this step.")
                return 1
        
        # Step 3: Optimize for TTS
        if not args.skip_to or args.skip_to <= 3:
            logger.info("Step 3: Optimizing for text-to-speech...")
            step3(
                client=big_text_client,
                config=config,
                input_file=transcript_file,
                output_dir=str(output_dirs["step3"]),
                preference_text=args.preference
            )
        else:
            logger.info("Skipping Step 3, assuming files exist in output directory...")
            # No need to find files here as step4 will look for them directly
        
        # Step 4: Generate audio
        if not args.skip_to or args.skip_to <= 4:
            logger.info("Step 4: Generating audio...")
            final_audio_path = step4(
                client=tts_client,
                config=config,
                dir=str(output_dirs["step3"])
            )
            
            logger.info(f"Podcast generation complete! Final audio file: {final_audio_path}")
        
        return 0
        
    except Exception as e:
        logger.error(f"Error during podcast generation: {str(e)}")
        return 1

if __name__ == "__main__":
    exit(main())