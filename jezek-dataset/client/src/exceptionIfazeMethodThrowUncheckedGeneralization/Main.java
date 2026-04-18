package exceptionIfazeMethodThrowUncheckedGeneralization;

import testing_lib.exceptionIfazeMethodThrowUncheckedGeneralization.ExceptionIfazeMethodThrowUncheckedGeneralization;

public class Main {

	public static void main(String[] args) {
		ExceptionIfazeMethodThrowUncheckedGeneralization constr = new ExceptionIfazeMethodThrowUncheckedGeneralization() {
			@Override public void method1() {}
		};
		constr.method1();
	}
	
}
