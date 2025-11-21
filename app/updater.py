import objc
import os
import sys

class SparkleManager:
    """
    Bridge to the Sparkle 2 Objective-C Framework.
    """
    def __init__(self):
        self.updater_controller = None
        try:
            self._load_sparkle()
            self._init_updater()
        except Exception as e:
            print(f"Sparkle: Failed to initialize: {e}")

    def _load_sparkle(self):
        """
        Dynamically load Sparkle.framework from the app bundle.
        """
        if getattr(sys, 'frozen', False):
            # In the frozen app, frameworks are usually in ../Frameworks relative to the executable
            bundle_path = os.path.dirname(sys.executable)
            framework_path = os.path.join(bundle_path, "..", "Frameworks", "Sparkle.framework")
            
            # Fallback: sometimes PyInstaller puts them elsewhere depending on config
            if not os.path.exists(framework_path):
                framework_path = os.path.join(bundle_path, "Sparkle.framework")
        else:
            # In development, point to where you put the downloaded framework
            # Adjust this path to match your folder structure!
            framework_path = os.path.abspath("frameworks/Sparkle.framework")

        if not os.path.exists(framework_path):
            raise FileNotFoundError(f"Sparkle framework not found at {framework_path}")

        # Load the bundle using PyObjC
        bundle = objc.loadBundle("Sparkle", globals(), bundle_path=framework_path)
        print(f"Sparkle: Loaded bundle {bundle}")

    def _init_updater(self):
        # SPUStandardUpdaterController is the standard entry point for Sparkle 2
        SPUStandardUpdaterController = objc.lookUpClass("SPUStandardUpdaterController")
        
        # Initialize with default settings (updater: True starts it automatically)
        self.updater_controller = SPUStandardUpdaterController.alloc().initWithStartingUpdater_(True, None)
        print("Sparkle: Updater controller initialized")

    def check_for_updates(self):
        if self.updater_controller:
            # 1. Get the SPUUpdater instance
            updater = self.updater_controller.updater()
            # 2. Call the check method
            updater.checkForUpdates_(None)
        else:
            print("Sparkle: Cannot check for updates, controller not initialized")