package exceptionIfazeMethodThrowUncheckedSpecialization;

import testing_lib.exceptionIfazeMethodThrowUncheckedSpecialization.ExceptionIfazeMethodThrowUncheckedSpecialization;

public class Main {

	public static void main(String[] args) {
		ExceptionIfazeMethodThrowUncheckedSpecialization constr = new ExceptionIfazeMethodThrowUncheckedSpecialization() {
			@Override public void method1() {}
		};
		constr.method1();
	}
	
}
