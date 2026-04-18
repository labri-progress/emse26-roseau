package exceptionIfazeMethodThrowCheckedMutation;

import java.io.FileNotFoundException;

import testing_lib.exceptionIfazeMethodThrowCheckedMutation.ExceptionIfazeMethodThrowCheckedMutation;

public class Main {

	public static void main(String[] args) {
		ExceptionIfazeMethodThrowCheckedMutation constr = new ExceptionIfazeMethodThrowCheckedMutation() {
			@Override public void method1() {}
		};
		try {
			constr.method1();
		} catch (FileNotFoundException e) {
			// TODO Auto-generated catch block
			e.printStackTrace();
		}
	}
}
