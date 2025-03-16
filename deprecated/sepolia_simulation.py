        
    except Exception as e:
        print(f"Error in simulation: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Stop Anvil process
        anvil.stop()


def run_sepolia_simulation():
    """Run the Sepolia simulation"""
    setup_sepolia_environment()


if __name__ == "__main__":
    run_sepolia_simulation()
    """Run the Sepolia simulation"""
    setup_sepolia_environment()


if __name__ == "__main__":
    run_sepolia_simulation()