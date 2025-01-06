- Make ProgramInterface a class as abstraction for the Interfaces - this will allow us to use the same interface for both the native, pulumi, dryrun and other interfaces
    - I don't know how to structure this part yet, but it should be possible to do
- Use real Pulumi modules in the PulumiInterface, instead of subprocess calls, to run as Pulumi instead of shell 
    - this may also be more correct in relation to resource management
- Rename MockInterface to NativeInterface, to make it more clear that it's not a mock, but a native python
- Make a DryRunInterface, that is a dryrun of the NativeInterface, That does not run the commands, but instead just logs the commands that would be run

With these changes would it be possible to create other interfaces for example dagger.io, or other tools?

After this Implementation is done, I will start working on the extension system, and how to make it possible to create extensions for the pipeline orchestrator.
