"""
Video Processor Package
Maneja descarga temporal de videos y extracción de frames
"""

from .frame_extractor import VideoFrameExtractor, extract_frames_from_url

__all__ = ['VideoFrameExtractor', 'extract_frames_from_url']
