Cauldron - Mocking up the KTL keyword system
--------------------------------------------


To use Cauldron, you must first select a backend::
    
    import Cauldron
    Cauldron.use("local")
    

Then, where you would have imported a KTL library, you can call::
    
    from Cauldron import ktl
    

or for the python dispatcher framework::
    
    from Cauldron import DFW
    

To use the standard KTL implementation, use the "KTL" backend::
    
    import Cauldron
    Cauldron.use("ktl")
    
